"""
Kosmos Integration Module for EAFramework

Integrates the full Kosmos literature search system with EAFramework's evolution loop.
Uses Gemini 3.0 Pro for concept extraction instead of Claude.

Features:
- Multi-source literature search (arXiv, Semantic Scholar, PubMed)
- Deep concept and method extraction from papers
- Caching for efficient re-use
- Formatted output for mutation prompts
"""

import logging
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

# Add Kosmos to path if available
KOSMOS_PATH = Path("/home/jupyter/Kosmos")
if KOSMOS_PATH.exists() and str(KOSMOS_PATH) not in sys.path:
    sys.path.insert(0, str(KOSMOS_PATH))

logger = logging.getLogger(__name__)


# =============================================================================
# KOSMOS IMPORTS (with fallbacks)
# =============================================================================

KOSMOS_AVAILABLE = False
try:
    from kosmos.literature.unified_search import UnifiedLiteratureSearch
    from kosmos.literature.base_client import PaperMetadata as KosmosPaperMetadata, PaperSource
    KOSMOS_AVAILABLE = True
    logger.info("鉁?Kosmos literature search available")
except ImportError as e:
    logger.warning(f"鈿狅笍 Kosmos not available: {e}")
    UnifiedLiteratureSearch = None
    KosmosPaperMetadata = None
    PaperSource = None

# Import local Gemini extractor
from ea.kosmos.gemini_concept_extractor import (
    GeminiConceptExtractor,
    PaperMetadata,
    ExtractionResult,
    ExtractedConcept,
    ExtractedMethod,
)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class LiteratureSearchResult:
    """Result from literature search with extracted concepts."""
    papers: List[PaperMetadata]
    extractions: List[ExtractionResult]
    query: str
    total_concepts: int
    total_methods: int
    sources_searched: List[str]


@dataclass
class Technique:
    """A technique extracted from literature (for mutation prompts)."""
    name: str
    description: str
    source: str  # 'paper_title' or 'paper_url'
    source_type: str  # 'arxiv', 'semantic_scholar', 'pubmed'
    relevance: float
    category: str = "unknown"  # loss_function, architecture, etc.
    implementation_hints: List[str] = None  # Bullet points for implementation
    code_snippet: Optional[str] = None
    
    def __post_init__(self):
        if self.implementation_hints is None:
            self.implementation_hints = []


# =============================================================================
# KOSMOS LITERATURE INTEGRATION
# =============================================================================

class KosmosLiteratureIntegration:
    """
    Full Kosmos literature search integration.
    
    Combines:
    1. Kosmos's UnifiedLiteratureSearch (arXiv + Semantic Scholar + PubMed)
    2. Gemini-based concept extraction
    3. Formatted output for EAFramework mutation prompts
    """
    
    def __init__(
        self,
        gemini_model: str = "gemini-3-pro-preview",
        enable_arxiv: bool = True,
        enable_semantic_scholar: bool = True,
        enable_pubmed: bool = False,  # Disabled by default (requires API key)
        semantic_scholar_api_key: Optional[str] = None,
        pubmed_api_key: Optional[str] = None,
        pubmed_email: Optional[str] = None,
        cache_dir: Optional[str] = ".kosmos_cache",
        verbose: bool = True
    ):
        """
        Initialize Kosmos literature integration.
        
        Args:
            gemini_model: Gemini model for concept extraction
            enable_arxiv: Enable arXiv search
            enable_semantic_scholar: Enable Semantic Scholar search
            enable_pubmed: Enable PubMed search
            semantic_scholar_api_key: Optional API key for Semantic Scholar
            pubmed_api_key: Optional API key for PubMed
            pubmed_email: Optional email for PubMed
            cache_dir: Directory for caching
            verbose: Print progress messages
        """
        self.verbose = verbose
        self.cache_dir = Path(cache_dir) if cache_dir else None
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize Kosmos search (if available)
        self.search_client = None
        self.sources_available = []
        
        if KOSMOS_AVAILABLE:
            try:
                # Try to initialize UnifiedLiteratureSearch
                # This may fail if Kosmos config is not properly set up
                self.search_client = UnifiedLiteratureSearch(
                    arxiv_enabled=enable_arxiv,
                    semantic_scholar_enabled=enable_semantic_scholar,
                    pubmed_enabled=enable_pubmed,
                    semantic_scholar_api_key=semantic_scholar_api_key,
                    pubmed_api_key=pubmed_api_key,
                    pubmed_email=pubmed_email
                )
                self.sources_available = list(self.search_client.clients.keys())
                if verbose:
                    logger.info(f"馃摎 Kosmos search initialized: {[s.value for s in self.sources_available]}")
            except Exception as e:
                logger.warning(f"Kosmos UnifiedSearch init failed: {e}")
                # Try fallback: just use arXiv client directly
                try:
                    from kosmos.literature.arxiv_client import ArxivClient
                    self.arxiv_client = ArxivClient()
                    if verbose:
                        logger.info("馃摎 Kosmos arXiv client initialized (direct)")
                except Exception as e2:
                    logger.warning(f"Kosmos arXiv client init failed: {e2}")
        else:
            if verbose:
                logger.warning("馃摎 Kosmos not available, using fallback arXiv search")
        
        # Initialize Gemini concept extractor
        self.extractor = GeminiConceptExtractor(
            model=gemini_model,
            cache_dir=str(self.cache_dir / "extractions") if self.cache_dir else None,
            use_cache=True,
            verbose=verbose
        )
        
        if verbose:
            logger.info(f"馃 Gemini extractor initialized: {gemini_model}")
    
    def search_and_extract(
        self,
        query: str,
        max_papers: int = 5,
        max_concepts_per_paper: int = 5,
        max_methods_per_paper: int = 3,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        extract_relationships: bool = False
    ) -> LiteratureSearchResult:
        """
        Search for papers and extract concepts/methods.
        
        Args:
            query: Search query
            max_papers: Maximum papers to retrieve
            max_concepts_per_paper: Max concepts per paper
            max_methods_per_paper: Max methods per paper
            year_from: Filter papers from this year
            year_to: Filter papers to this year
            extract_relationships: Whether to extract concept relationships
        
        Returns:
            LiteratureSearchResult with papers and extractions
        """
        if self.verbose:
            logger.info(f"馃攳 Searching: {query[:50]}...")
        
        # Search for papers
        if self.search_client and KOSMOS_AVAILABLE:
            papers = self._search_kosmos(query, max_papers, year_from, year_to)
            sources = [s.value for s in self.sources_available]
        elif hasattr(self, 'arxiv_client') and self.arxiv_client:
            papers = self._search_kosmos_arxiv_direct(query, max_papers)
            sources = ['arxiv_kosmos']
        else:
            papers = self._search_fallback(query, max_papers)
            sources = ['arxiv_fallback']
        
        if self.verbose:
            logger.info(f"馃搫 Found {len(papers)} papers")
        
        # Extract concepts and methods
        extractions = []
        total_concepts = 0
        total_methods = 0
        
        for paper in papers:
            try:
                result = self.extractor.extract_from_paper(
                    paper,
                    include_relationships=extract_relationships,
                    max_concepts=max_concepts_per_paper,
                    max_methods=max_methods_per_paper
                )
                extractions.append(result)
                total_concepts += len(result.concepts)
                total_methods += len(result.methods)
            except Exception as e:
                logger.error(f"Extraction failed for {paper.title[:30]}: {e}")
                extractions.append(ExtractionResult(
                    paper_id=paper.primary_identifier,
                    concepts=[],
                    methods=[],
                    relationships=[],
                    extraction_time=0.0,
                    model_used=self.extractor.model
                ))
        
        if self.verbose:
            logger.info(f"馃 Extracted {total_concepts} concepts, {total_methods} methods")
        
        return LiteratureSearchResult(
            papers=papers,
            extractions=extractions,
            query=query,
            total_concepts=total_concepts,
            total_methods=total_methods,
            sources_searched=sources
        )
    
    def _search_kosmos(
        self,
        query: str,
        max_papers: int,
        year_from: Optional[int],
        year_to: Optional[int]
    ) -> List[PaperMetadata]:
        """Search using Kosmos's unified search."""
        try:
            kosmos_papers = self.search_client.search(
                query=query,
                max_results_per_source=max_papers,
                total_max_results=max_papers,
                year_from=year_from,
                year_to=year_to,
                deduplicate=True,
                extract_full_text=False  # Abstracts are usually enough
            )
            
            # Convert to our PaperMetadata format
            papers = []
            for kp in kosmos_papers:
                papers.append(PaperMetadata(
                    title=kp.title or "Unknown",
                    abstract=kp.abstract or "",
                    url=kp.url or "",
                    id=kp.id or "",
                    primary_identifier=kp.primary_identifier or kp.id or "",
                    doi=kp.doi or "",
                    arxiv_id=kp.arxiv_id or "",
                    pubmed_id=kp.pubmed_id or "",
                    authors=kp.authors or [],
                    published=kp.published or "",
                    full_text=kp.full_text or "",
                    source=kp.source.value if hasattr(kp, 'source') and kp.source else "unknown"
                ))
            
            return papers
        except Exception as e:
            logger.error(f"Kosmos search failed: {e}")
            return self._search_fallback(query, max_papers)
    
    def _search_kosmos_arxiv_direct(
        self,
        query: str,
        max_papers: int
    ) -> List[PaperMetadata]:
        """Search using Kosmos's ArxivClient directly (when UnifiedSearch fails)."""
        try:
            kosmos_papers = self.arxiv_client.search(query, max_results=max_papers)
            
            papers = []
            for kp in kosmos_papers:
                papers.append(PaperMetadata(
                    title=kp.title or "Unknown",
                    abstract=kp.abstract or "",
                    url=kp.url or "",
                    id=kp.id or "",
                    primary_identifier=kp.primary_identifier or kp.id or "",
                    doi=kp.doi or "",
                    arxiv_id=kp.arxiv_id or "",
                    authors=kp.authors or [],
                    published=kp.published or "",
                    source="arxiv"
                ))
            
            return papers
        except Exception as e:
            logger.error(f"Kosmos arXiv direct search failed: {e}")
            return self._search_fallback(query, max_papers)
    
    def _search_fallback(self, query: str, max_papers: int) -> List[PaperMetadata]:
        """Fallback to simple arXiv search."""
        try:
            from ea.kosmos.simple_paper_search import SimplePaperSearch
            searcher = SimplePaperSearch(verbose=self.verbose)
            simple_papers = searcher.search(query, max_results=max_papers)
            
            papers = []
            for sp in simple_papers:
                papers.append(PaperMetadata(
                    title=sp.title,
                    abstract=sp.abstract,
                    url=sp.url,
                    authors=sp.authors.split(", ") if sp.authors else [],
                    published=sp.published or "",
                    source="arxiv"
                ))
            
            return papers
        except Exception as e:
            logger.error(f"Fallback search failed: {e}")
            return []
    
    def get_techniques_for_prompt(
        self,
        search_result: LiteratureSearchResult,
        max_techniques: int = 10
    ) -> List[Technique]:
        """
        Convert extraction results to techniques for mutation prompts.
        
        Args:
            search_result: Result from search_and_extract
            max_techniques: Maximum techniques to return
        
        Returns:
            List of Technique objects
        """
        techniques = []
        
        for paper, extraction in zip(search_result.papers, search_result.extractions):
            # Add methods as techniques (higher priority - they have implementation details)
            for method in extraction.methods:
                techniques.append(Technique(
                    name=method.name,
                    description=method.description,
                    source=paper.title,
                    source_type=paper.source,
                    relevance=method.confidence,
                    category=method.category,
                    implementation_hints=method.implementation_hints if hasattr(method, 'implementation_hints') else [],
                    code_snippet=method.code_snippet if hasattr(method, 'code_snippet') else None
                ))
            
            # Add high-relevance concepts as techniques (but lower priority than methods)
            for concept in extraction.concepts:
                if concept.relevance >= 0.8:  # Increased threshold
                    techniques.append(Technique(
                        name=concept.name,
                        description=concept.description,
                        source=paper.title,
                        source_type=paper.source,
                        relevance=concept.relevance * 0.9,  # Slightly lower than methods
                        category="concept",
                        implementation_hints=[],
                        code_snippet=None
                    ))
        
        # Sort by relevance and limit
        techniques.sort(key=lambda t: t.relevance, reverse=True)
        return techniques[:max_techniques]
    
    def format_for_mutation_prompt(
        self,
        search_result: LiteratureSearchResult,
        max_techniques: int = 10
    ) -> str:
        """
        Format search results for mutation prompt injection with DETAILED implementation guidance.
        
        Args:
            search_result: Result from search_and_extract
            max_techniques: Maximum techniques to include
        
        Returns:
            Formatted string for prompt injection
        """
        techniques = self.get_techniques_for_prompt(search_result, max_techniques)
        
        if not techniques:
            return "(No techniques extracted from literature)"
        
        lines = [
            "# 馃摎 TECHNIQUES FROM SCIENTIFIC LITERATURE",
            "",
            f"Query: \"{search_result.query}\"",
            f"Sources: {', '.join(search_result.sources_searched)}",
            f"Papers analyzed: {len(search_result.papers)}",
            f"Techniques extracted: {len(techniques)}",
            "",
            "**INSTRUCTION: Use these techniques to improve your code. Each technique includes implementation guidance and code snippets.**",
            "",
            "=" * 60,
            ""
        ]
        
        for i, tech in enumerate(techniques, 1):
            lines.append(f"## [{i}] {tech.name}")
            lines.append(f"**Category:** {tech.category}")
            lines.append(f"**Source:** {tech.source[:60]}... ({tech.source_type})")
            lines.append(f"**Relevance:** {tech.relevance:.2f}")
            lines.append("")
            lines.append("### Description")
            lines.append(tech.description)
            lines.append("")
            
            # Add implementation hints if available
            if tech.implementation_hints:
                lines.append("### Implementation Hints")
                for hint in tech.implementation_hints:
                    lines.append(f"- {hint}")
                lines.append("")
            
            # Add code snippet if available
            if tech.code_snippet:
                lines.append("### Code Snippet")
                lines.append("```python")
                lines.append(tech.code_snippet)
                lines.append("```")
                lines.append("")
            
            lines.append("-" * 40)
            lines.append("")
        
        lines.append("")
        lines.append("=" * 60)
        lines.append("")
        lines.append("**YOUR TASK:** Implement one or more of these techniques in the EVOLVE-BLOCK region.")
        lines.append("Focus on techniques that address class imbalance, hierarchy consistency, or feature engineering.")
        
        return "\n".join(lines)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def search_literature(
    query: str,
    max_papers: int = 5,
    extract_concepts: bool = True,
    gemini_model: str = "gemini-3-pro-preview"
) -> str:
    """
    Convenience function to search literature and format for prompts.
    
    Args:
        query: Search query
        max_papers: Maximum papers
        extract_concepts: Whether to extract concepts (slower but richer)
        gemini_model: Gemini model to use
    
    Returns:
        Formatted string for prompt injection
    """
    integration = KosmosLiteratureIntegration(
        gemini_model=gemini_model,
        enable_arxiv=True,
        enable_semantic_scholar=True,
        enable_pubmed=False,
        verbose=True
    )
    
    if extract_concepts:
        result = integration.search_and_extract(
            query=query,
            max_papers=max_papers,
            max_concepts_per_paper=5,
            max_methods_per_paper=3
        )
        return integration.format_for_mutation_prompt(result)
    else:
        # Simple search without extraction
        if integration.search_client and KOSMOS_AVAILABLE:
            papers = integration._search_kosmos(query, max_papers, None, None)
        else:
            papers = integration._search_fallback(query, max_papers)
        
        lines = ["# 馃摎 PAPERS FROM SCIENTIFIC LITERATURE", "", f"Query: \"{query}\"", "", "---", ""]
        for i, paper in enumerate(papers, 1):
            lines.append(f"### [{i}] {paper.title}")
            lines.append(f"**Abstract:** {paper.abstract[:300]}...")
            lines.append(f"**URL:** {paper.url}")
            lines.append("")
        
        return "\n".join(lines)


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    # Test the integration
    logging.basicConfig(level=logging.INFO)
    
    print("Testing Kosmos Literature Integration...")
    print("="*60)
    
    integration = KosmosLiteratureIntegration(
        gemini_model="gemini-3-pro-preview",
        enable_arxiv=True,
        enable_semantic_scholar=True,
        enable_pubmed=False,
        verbose=True
    )
    
    result = integration.search_and_extract(
        query="protein function prediction deep learning GO ontology",
        max_papers=3,
        max_concepts_per_paper=5,
        max_methods_per_paper=3
    )
    
    print("\n" + "="*60)
    print("FORMATTED OUTPUT:")
    print("="*60)
    print(integration.format_for_mutation_prompt(result))

