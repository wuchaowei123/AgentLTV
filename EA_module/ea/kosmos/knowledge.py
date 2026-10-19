"""
Hybrid Knowledge Manager

Manages knowledge from multiple sources:
1. LLM's built-in knowledge (always available)
2. Literature search (arXiv, Semantic Scholar) - triggered on plateau
3. Web search (Gemini with Google Search grounding) - triggered on plateau
4. Human knowledge base (curated YAML)
"""

import os
import json
import yaml
import time
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import requests
import logging

# Import simple paper search for direct abstract injection (legacy)
try:
    from .simple_paper_search import SimplePaperSearch
except ImportError:
    SimplePaperSearch = None

# Import full Kosmos literature integration (NEW - uses Gemini 3.0 Pro)
try:
    from .kosmos_integration import KosmosLiteratureIntegration
    KOSMOS_INTEGRATION_AVAILABLE = True
except ImportError:
    KosmosLiteratureIntegration = None
    KOSMOS_INTEGRATION_AVAILABLE = False

# Import Kaggle integration modules
try:
    from .kaggle_client import KaggleNotebookClient, KaggleNotebook
    KAGGLE_CLIENT_AVAILABLE = True
except ImportError:
    KaggleNotebookClient = None
    KaggleNotebook = None
    KAGGLE_CLIENT_AVAILABLE = False

try:
    from .kaggle_scraper import KaggleDiscussionScraper, KaggleDiscussion
    KAGGLE_SCRAPER_AVAILABLE = True
except ImportError:
    KaggleDiscussionScraper = None
    KaggleDiscussion = None
    KAGGLE_SCRAPER_AVAILABLE = False

try:
    from .kaggle_analyzer import KaggleTechniqueAnalyzer, ExtractedTechnique
    KAGGLE_ANALYZER_AVAILABLE = True
except ImportError:
    KaggleTechniqueAnalyzer = None
    ExtractedTechnique = None
    KAGGLE_ANALYZER_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class Technique:
    """A technique from any knowledge source"""
    name: str
    description: str
    source: str  # 'llm', 'arxiv', 'semantic_scholar', 'web', 'human'
    code_example: Optional[str] = None
    applicable_when: Optional[str] = None
    relevance_score: float = 0.5
    url: Optional[str] = None  # Link to source
    
    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'description': self.description,
            'source': self.source,
            'code_example': self.code_example,
            'applicable_when': self.applicable_when,
            'relevance_score': self.relevance_score,
            'url': self.url
        }


@dataclass
class KnowledgeBundle:
    """Bundle of knowledge from all sources"""
    human_knowledge: List[Technique] = field(default_factory=list)
    literature: List[Technique] = field(default_factory=list)
    web: List[Technique] = field(default_factory=list)
    cached: List[Technique] = field(default_factory=list)
    kaggle_notebooks: List[Technique] = field(default_factory=list)  # NEW: Kaggle notebook techniques
    kaggle_discussions: List[Technique] = field(default_factory=list)  # NEW: Kaggle discussion insights
    paper_abstracts: str = ""  # Raw paper abstracts for direct LLM injection
    search_performed: bool = False
    search_reason: Optional[str] = None
    
    def all_techniques(self) -> List[Technique]:
        """Get all techniques from all sources"""
        return (
            self.human_knowledge + 
            self.literature + 
            self.web + 
            self.cached +
            self.kaggle_notebooks +
            self.kaggle_discussions
        )
    
    def to_dict(self) -> dict:
        return {
            'human_knowledge': [t.to_dict() for t in self.human_knowledge],
            'literature': [t.to_dict() for t in self.literature],
            'web': [t.to_dict() for t in self.web],
            'cached': [t.to_dict() for t in self.cached],
            'kaggle_notebooks': [t.to_dict() for t in self.kaggle_notebooks],
            'kaggle_discussions': [t.to_dict() for t in self.kaggle_discussions],
            'paper_abstracts': self.paper_abstracts,
            'search_performed': self.search_performed,
            'search_reason': self.search_reason
        }


class NoveltySearchTrigger:
    """
    Decides WHEN to search for external knowledge.
    
    Triggers:
    1. Plateau: No improvement for N generations
    2. Stagnation: Same techniques repeated
    3. Periodic: Every M generations (maintenance)
    """
    
    def __init__(
        self,
        plateau_threshold: int = 10,
        stagnation_threshold: int = 3,
        periodic_interval: int = 30,
        min_generations: int = 20,
        search_cooldown: int = 15
    ):
        self.plateau_threshold = plateau_threshold
        self.stagnation_threshold = stagnation_threshold
        self.periodic_interval = periodic_interval
        self.min_generations = min_generations
        self.search_cooldown = search_cooldown
        
        self.last_search_gen = 0
    
    def should_search(
        self, 
        current_gen: int, 
        history: List[Dict[str, Any]]
    ) -> tuple[bool, Optional[str]]:
        """
        Determine if external knowledge search is needed.
        
        Returns:
            (should_search, reason)
        """
        # Rule 1: Don't search in early exploration
        if current_gen < self.min_generations:
            return False, None
        
        # Rule 2: Respect cooldown period
        if current_gen - self.last_search_gen < self.search_cooldown:
            return False, None
        
        # Rule 3: Periodic maintenance search
        if current_gen % self.periodic_interval == 0:
            return True, f"Periodic refresh (every {self.periodic_interval} gens)"
        
        # Rule 4: Plateau detection
        if self._detect_plateau(history):
            return True, f"Plateau detected ({self.plateau_threshold}+ gens without improvement)"
        
        # Rule 5: Stagnation detection
        if self._detect_stagnation(history):
            return True, f"Stagnation detected (< {self.stagnation_threshold} unique techniques)"
        
        return False, None
    
    def _detect_plateau(self, history: List[Dict[str, Any]]) -> bool:
        """Check if score hasn't improved in N generations"""
        if len(history) < self.plateau_threshold:
            return False
        
        recent = history[-self.plateau_threshold:]
        earlier = history[:-self.plateau_threshold]
        
        if not earlier:
            return False
        
        # Get best scores
        def get_score(h):
            return h.get('score', h.get('f1', h.get('combined_score', 0)))
        
        best_recent = max(get_score(h) for h in recent)
        best_earlier = max(get_score(h) for h in earlier)
        
        # Plateau if improvement < 1%
        return (best_recent - best_earlier) < 0.01
    
    def _detect_stagnation(self, history: List[Dict[str, Any]]) -> bool:
        """Check if we're repeating the same techniques"""
        if len(history) < 10:
            return False
        
        recent_techniques = [
            h.get('model_type', h.get('technique', 'unknown'))
            for h in history[-10:]
        ]
        unique_count = len(set(recent_techniques))
        
        return unique_count < self.stagnation_threshold
    
    def record_search(self, gen: int):
        """Record that a search was performed"""
        self.last_search_gen = gen


class HumanKnowledgeBase:
    """Curated knowledge from human experts"""
    
    def __init__(self, kb_path: Optional[str] = None):
        self.kb_path = kb_path
        self.techniques: List[Dict[str, Any]] = []
        
        if kb_path and Path(kb_path).exists():
            self._load_kb()
    
    def _load_kb(self):
        """Load knowledge base from YAML"""
        try:
            with open(self.kb_path, 'r') as f:
                data = yaml.safe_load(f)
                self.techniques = data.get('techniques', [])
        except Exception as e:
            print(f"鈿狅笍  Error loading knowledge base: {e}")
    
    def get_relevant(self, task_description: str) -> List[Technique]:
        """Get relevant techniques for the task"""
        relevant = []
        
        task_lower = task_description.lower()
        
        for tech in self.techniques:
            # Simple relevance check
            applicable = tech.get('applicable_when', '').lower()
            name = tech.get('name', '').lower()
            desc = tech.get('description', '').lower()
            
            # Check if task matches applicable conditions
            is_relevant = (
                'general' in applicable or
                any(word in task_lower for word in applicable.split()) or
                any(word in task_lower for word in name.split()) or
                any(word in task_lower for word in desc.split()[:10])
            )
            
            if is_relevant:
                relevant.append(Technique(
                    name=tech.get('name', 'Unknown'),
                    description=tech.get('description', ''),
                    source='human',
                    code_example=tech.get('code_example'),
                    applicable_when=tech.get('applicable_when'),
                    relevance_score=0.8  # Human-curated = high relevance
                ))
        
        return relevant
    
    def add_technique(self, technique: Dict[str, Any]):
        """Add a new technique to the knowledge base"""
        self.techniques.append(technique)
        if self.kb_path:
            self._save_kb()
    
    def _save_kb(self):
        """Save knowledge base to YAML"""
        try:
            with open(self.kb_path, 'w') as f:
                yaml.dump({'techniques': self.techniques}, f, default_flow_style=False)
        except Exception as e:
            print(f"鈿狅笍  Error saving knowledge base: {e}")


class ArxivSearch:
    """Search arXiv for academic papers (FREE, no API key needed)"""
    
    ARXIV_API_URL = "https://export.arxiv.org/api/query"  # Must use HTTPS
    
    # Track last request time to avoid rate limiting
    _last_request_time = 0.0
    _min_request_interval = 3.0  # Minimum 3 seconds between requests
    
    def __init__(self, verbose: bool = True, max_retries: int = 3, retry_delay: float = 5.0):
        self.verbose = verbose
        self.max_retries = max_retries
        self.retry_delay = retry_delay
    
    def search(
        self,
        query: str,
        max_results: int = 5
    ) -> List[Technique]:
        """
        Search arXiv for relevant papers with retry logic.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            List of Technique objects from papers
        """
        if self.verbose:
            logger.info(f"馃摎 arXiv search: {query[:50]}...")
        
        # Build arXiv query - keep it simple for better results
        # Use simpler query format to avoid timeout issues
        # Extract first 3 key words from query
        query_words = query.split()[:5]
        arxiv_query = ' '.join(query_words)
        
        params = {
            'search_query': f'all:{arxiv_query}',
            'start': 0,
            'max_results': max_results,
            'sortBy': 'relevance',
            'sortOrder': 'descending'
        }
        
        # Respect rate limiting - wait if needed
        time_since_last = time.time() - ArxivSearch._last_request_time
        if time_since_last < ArxivSearch._min_request_interval:
            wait_time = ArxivSearch._min_request_interval - time_since_last
            if self.verbose:
                logger.info(f"   Waiting {wait_time:.1f}s to respect arXiv rate limit...")
            time.sleep(wait_time)
        
        # Retry with exponential backoff
        for attempt in range(self.max_retries):
            try:
                # Add delay between retries (exponential backoff)
                if attempt > 0:
                    delay = self.retry_delay * (2 ** (attempt - 1))
                    if self.verbose:
                        logger.info(f"   Retry {attempt + 1}/{self.max_retries} after {delay}s delay...")
                    time.sleep(delay)
                
                ArxivSearch._last_request_time = time.time()
                response = requests.get(self.ARXIV_API_URL, params=params, timeout=60)  # Increased timeout
                
                # Handle rate limiting specifically
                if response.status_code == 429:
                    if self.verbose:
                        logger.warning(f"   arXiv rate limited, retrying...")
                    continue
                
                response.raise_for_status()
                
                # Parse XML response
                techniques = self._parse_arxiv_response(response.text)
                
                if self.verbose:
                    logger.info(f"   Found {len(techniques)} papers from arXiv")
                
                return techniques
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429 and attempt < self.max_retries - 1:
                    continue  # Retry on rate limit
                if self.verbose:
                    logger.warning(f"鈿狅笍  arXiv search failed (attempt {attempt + 1}): {e}")
            except Exception as e:
                if self.verbose:
                    logger.warning(f"鈿狅笍  arXiv search failed (attempt {attempt + 1}): {e}")
        
        return []
    
    def _parse_arxiv_response(self, xml_text: str) -> List[Technique]:
        """Parse arXiv XML response into Technique objects"""
        import xml.etree.ElementTree as ET
        
        techniques = []
        
        try:
            root = ET.fromstring(xml_text)
            
            # arXiv uses Atom namespace
            ns = {
                'atom': 'http://www.w3.org/2005/Atom',
                'arxiv': 'http://arxiv.org/schemas/atom'
            }
            
            for entry in root.findall('atom:entry', ns):
                title = entry.find('atom:title', ns)
                summary = entry.find('atom:summary', ns)
                link = entry.find("atom:link[@type='text/html']", ns)
                
                if title is not None and summary is not None:
                    title_text = title.text.strip().replace('\n', ' ')
                    summary_text = summary.text.strip().replace('\n', ' ')[:500]
                    url = link.get('href') if link is not None else None
                    
                    # Extract key techniques from abstract
                    technique = Technique(
                        name=title_text[:100],
                        description=summary_text,
                        source='arxiv',
                        relevance_score=0.7,
                        url=url
                    )
                    techniques.append(technique)
        
        except Exception as e:
            logger.warning(f"Error parsing arXiv response: {e}")
        
        return techniques


class SemanticScholarSearch:
    """Search Semantic Scholar for academic papers (FREE, no API key for basic use)"""
    
    API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
    
    def __init__(self, verbose: bool = True, max_retries: int = 3, retry_delay: float = 2.0):
        self.verbose = verbose
        self.max_retries = max_retries
        self.retry_delay = retry_delay
    
    def search(
        self,
        query: str,
        max_results: int = 5
    ) -> List[Technique]:
        """
        Search Semantic Scholar for relevant papers with retry logic.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            List of Technique objects from papers
        """
        if self.verbose:
            logger.info(f"馃摉 Semantic Scholar search: {query[:50]}...")
        
        params = {
            'query': query,
            'limit': max_results,
            'fields': 'title,abstract,url,year,citationCount'
        }
        
        headers = {
            'User-Agent': 'EAFramework/1.0 (research project)'
        }
        
        # Retry with exponential backoff
        for attempt in range(self.max_retries):
            try:
                # Add delay between retries (exponential backoff)
                if attempt > 0:
                    delay = self.retry_delay * (2 ** (attempt - 1))
                    if self.verbose:
                        logger.info(f"   Retry {attempt + 1}/{self.max_retries} after {delay}s delay...")
                    time.sleep(delay)
                
                response = requests.get(self.API_URL, params=params, headers=headers, timeout=30)
                
                # Handle rate limiting specifically
                if response.status_code == 429:
                    if self.verbose:
                        logger.warning(f"   Semantic Scholar rate limited, retrying...")
                    continue
                
                response.raise_for_status()
                
                data = response.json()
                techniques = self._parse_response(data)
                
                if self.verbose:
                    logger.info(f"   Found {len(techniques)} papers from Semantic Scholar")
                
                return techniques
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429 and attempt < self.max_retries - 1:
                    continue  # Retry on rate limit
                if self.verbose:
                    logger.warning(f"鈿狅笍  Semantic Scholar search failed (attempt {attempt + 1}): {e}")
            except Exception as e:
                if self.verbose:
                    logger.warning(f"鈿狅笍  Semantic Scholar search failed (attempt {attempt + 1}): {e}")
        
        return []
    
    def _parse_response(self, data: Dict[str, Any]) -> List[Technique]:
        """Parse Semantic Scholar response into Technique objects"""
        techniques = []
        
        papers = data.get('data', [])
        
        for paper in papers:
            title = paper.get('title', 'Unknown')
            abstract = paper.get('abstract', '')
            url = paper.get('url', '')
            year = paper.get('year', 0)
            citations = paper.get('citationCount', 0)
            
            if abstract:
                # Calculate relevance based on recency and citations
                recency_score = min(1.0, (year - 2020) / 5) if year else 0.5
                citation_score = min(1.0, citations / 100) if citations else 0.3
                relevance = 0.5 + 0.25 * recency_score + 0.25 * citation_score
                
                technique = Technique(
                    name=title[:100],
                    description=abstract[:500] if abstract else f"Paper from {year}",
                    source='semantic_scholar',
                    relevance_score=relevance,
                    url=url
                )
                techniques.append(technique)
        
        return techniques


class GeminiWebSearch:
    """Search web using Gemini with Google Search grounding"""
    
    def __init__(
        self,
        project_id: str = "prefab-root-439302-c5",
        location: str = "us-central1",
        model: str = "gemini-2.5-pro",
        verbose: bool = True
    ):
        self.project_id = project_id
        self.location = location
        self.model = model
        self.verbose = verbose
        self._client = None
    
    def _get_client(self):
        """Lazy initialization of Gemini client"""
        if self._client is None:
            try:
                from google import genai
                self._client = genai.Client(
                    vertexai=True,
                    project=self.project_id,
                    location=self.location
                )
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini client: {e}")
                return None
        return self._client
    
    def search(
        self,
        query: str,
        max_results: int = 5
    ) -> List[Technique]:
        """
        Search web using Gemini with Google Search grounding.
        
        Args:
            query: Search query
            max_results: Maximum number of techniques to extract
            
        Returns:
            List of Technique objects from web search
        """
        if self.verbose:
            logger.info(f"馃寪 Gemini web search: {query[:50]}...")
        
        client = self._get_client()
        if client is None:
            return []
        
        try:
            from google.genai import types
            
            # Craft a prompt to extract actionable techniques
            search_prompt = f"""Search for the latest machine learning techniques related to:
{query}

For each technique you find, provide:
1. Name of the technique
2. Brief description (2-3 sentences)
3. When to use it
4. A simple code example if applicable

Focus on practical, implementable techniques from 2023-2025.
Return up to {max_results} most relevant techniques."""
            
            response = client.models.generate_content(
                model=self.model,
                contents=search_prompt,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                    temperature=0.3
                )
            )
            
            # Parse the response to extract techniques
            techniques = self._parse_gemini_response(response.text)
            
            if self.verbose:
                logger.info(f"   Extracted {len(techniques)} techniques from web search")
            
            return techniques
            
        except Exception as e:
            if self.verbose:
                logger.warning(f"鈿狅笍  Gemini web search failed: {e}")
            return []
    
    def _parse_gemini_response(self, text: str) -> List[Technique]:
        """Parse Gemini response to extract techniques"""
        techniques = []
        
        if not text:
            return techniques
        
        # Split by numbered items or headers
        # Look for patterns like "1.", "##", "**Name:**", etc.
        sections = re.split(r'\n(?=\d+\.|#{1,3}\s|(?:\*\*|\#))', text)
        
        for section in sections:
            if len(section.strip()) < 50:
                continue
            
            # Try to extract technique name and description
            lines = section.strip().split('\n')
            
            # First non-empty line is likely the name
            name = ""
            description = ""
            code_example = None
            
            for i, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                
                # Remove markdown formatting
                clean_line = re.sub(r'[\*\#\d+\.\:]', '', line).strip()
                
                if not name and len(clean_line) > 5:
                    name = clean_line[:100]
                elif name and not description:
                    description = clean_line
                    # Collect more description lines
                    for j in range(i+1, min(i+4, len(lines))):
                        next_line = lines[j].strip()
                        if next_line and not next_line.startswith('```'):
                            description += " " + re.sub(r'[\*\#]', '', next_line)
                        elif next_line.startswith('```'):
                            break
                    break
            
            # Look for code blocks
            code_match = re.search(r'```(?:python)?\n?(.*?)```', section, re.DOTALL)
            if code_match:
                code_example = code_match.group(1).strip()[:300]
            
            if name and description:
                technique = Technique(
                    name=name,
                    description=description[:500],
                    source='web',
                    code_example=code_example,
                    relevance_score=0.6
                )
                techniques.append(technique)
        
        return techniques[:5]  # Limit to 5 techniques


class LiteratureSearch:
    """Combined literature search using arXiv and Semantic Scholar"""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.arxiv = ArxivSearch(verbose=verbose)
        self.semantic_scholar = SemanticScholarSearch(verbose=verbose)
    
    def search(
        self,
        query: str,
        max_results: int = 5
    ) -> List[Technique]:
        """
        Search for relevant papers from multiple sources.
        
        Args:
            query: Search query
            max_results: Maximum number of results per source
            
        Returns:
            Combined list of Technique objects from papers
        """
        if self.verbose:
            logger.info(f"馃摎 Literature search: {query[:50]}...")
        
        techniques = []
        
        # Search arXiv
        arxiv_results = self.arxiv.search(query, max_results=max_results)
        techniques.extend(arxiv_results)
        
        # Add small delay to be respectful to APIs
        time.sleep(0.5)
        
        # Search Semantic Scholar
        ss_results = self.semantic_scholar.search(query, max_results=max_results)
        techniques.extend(ss_results)
        
        # Sort by relevance and deduplicate
        techniques = self._deduplicate(techniques)
        techniques.sort(key=lambda t: t.relevance_score, reverse=True)
        
        return techniques[:max_results * 2]  # Return up to 2x max_results
    
    def _deduplicate(self, techniques: List[Technique]) -> List[Technique]:
        """Remove duplicate techniques based on name similarity"""
        seen_names = set()
        unique = []
        
        for t in techniques:
            # Normalize name for comparison
            normalized = t.name.lower().strip()[:50]
            if normalized not in seen_names:
                seen_names.add(normalized)
                unique.append(t)
        
        return unique


class WebSearch:
    """Web search using Gemini with Google Search grounding"""
    
    def __init__(
        self,
        project_id: str = "prefab-root-439302-c5",
        location: str = "us-central1",
        model: str = "gemini-2.5-pro",
        verbose: bool = True
    ):
        self.verbose = verbose
        self.gemini_search = GeminiWebSearch(
            project_id=project_id,
            location=location,
            model=model,
            verbose=verbose
        )
    
    def search(
        self,
        query: str,
        max_results: int = 5
    ) -> List[Technique]:
        """
        Search web for recent techniques using Gemini.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            List of Technique objects from web search
        """
        return self.gemini_search.search(query, max_results)


@dataclass
class HumanGuidance:
    """Human guidance for evolution"""
    priorities: List[str] = field(default_factory=list)  # High priority suggestions
    try_ideas: List[str] = field(default_factory=list)   # Ideas to try
    avoid: List[str] = field(default_factory=list)       # Things to avoid
    focus: List[str] = field(default_factory=list)       # Areas to focus on
    notes: List[str] = field(default_factory=list)       # General notes
    last_updated: Optional[str] = None
    
    def is_empty(self) -> bool:
        return not (self.priorities or self.try_ideas or self.avoid or self.focus or self.notes)
    
    def to_prompt_text(self) -> str:
        """Format guidance for injection into LLM prompt"""
        if self.is_empty():
            return ""
        
        lines = [
            "",
            "鈺? * 60,
            "馃幆 HUMAN GUIDANCE (Real-time steering from researcher)",
            "鈺? * 60,
        ]
        
        if self.last_updated:
            lines.append(f"Last updated: {self.last_updated}")
            lines.append("")
        
        if self.priorities:
            lines.append("馃敶 HIGH PRIORITY (Do this first!):")
            for p in self.priorities:
                lines.append(f"   鈥?{p}")
            lines.append("")
        
        if self.try_ideas:
            lines.append("馃挕 TRY THESE IDEAS:")
            for t in self.try_ideas:
                lines.append(f"   鈥?{t}")
            lines.append("")
        
        if self.focus:
            lines.append("馃攳 FOCUS ON:")
            for f in self.focus:
                lines.append(f"   鈥?{f}")
            lines.append("")
        
        if self.avoid:
            lines.append("鉀?AVOID (Don't do these):")
            for a in self.avoid:
                lines.append(f"   鈥?{a}")
            lines.append("")
        
        if self.notes:
            lines.append("馃摑 NOTES:")
            for n in self.notes:
                lines.append(f"   鈥?{n}")
            lines.append("")
        
        lines.append("Please consider this guidance when generating mutations!")
        lines.append("鈺? * 60)
        
        return "\n".join(lines)


class HumanGuidanceReader:
    """
    Reads human guidance from a text file for real-time steering.
    
    File format (human_guidance.txt):
    ```
    # Human Guidance for Evolution
    # Last updated: 2025-11-28 09:00
    
    PRIORITY: Try XGBoost instead of LightGBM
    PRIORITY: Focus on feature interactions
    
    TRY: Add user session duration features
    TRY: Use attention mechanisms on embeddings
    
    AVOID: Don't use too many ensemble models
    AVOID: Skip complex neural networks (too slow)
    
    FOCUS: Explore temporal patterns
    FOCUS: User behavior sequences
    
    NOTE: Current best uses hyperbolic features
    NOTE: Cycle features seem important
    ```
    """
    
    def __init__(
        self,
        guidance_file_path: Optional[str] = None,
        verbose: bool = True
    ):
        self.guidance_file_path = guidance_file_path
        self.verbose = verbose
        self._last_modified_time = 0.0
        self._cached_guidance: Optional[HumanGuidance] = None
    
    def read_guidance(self) -> HumanGuidance:
        """
        Read guidance from file. Caches result and only re-reads if file changed.
        
        Returns:
            HumanGuidance object with parsed guidance
        """
        if not self.guidance_file_path:
            return HumanGuidance()
        
        path = Path(self.guidance_file_path)
        if not path.exists():
            if self.verbose:
                logger.info(f"馃摑 Human guidance file not found: {path}")
            return HumanGuidance()
        
        # Check if file was modified
        try:
            current_mtime = path.stat().st_mtime
            if current_mtime == self._last_modified_time and self._cached_guidance:
                return self._cached_guidance
            
            self._last_modified_time = current_mtime
        except Exception as e:
            logger.warning(f"Error checking guidance file: {e}")
            return HumanGuidance()
        
        # Parse the file
        guidance = self._parse_guidance_file(path)
        self._cached_guidance = guidance
        
        if self.verbose and not guidance.is_empty():
            logger.info(f"馃摑 Loaded human guidance:")
            logger.info(f"   Priorities: {len(guidance.priorities)}")
            logger.info(f"   Try ideas: {len(guidance.try_ideas)}")
            logger.info(f"   Focus areas: {len(guidance.focus)}")
            logger.info(f"   Avoid: {len(guidance.avoid)}")
        
        return guidance
    
    def _parse_guidance_file(self, path: Path) -> HumanGuidance:
        """Parse the guidance file"""
        guidance = HumanGuidance()
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract last updated from comments
            updated_match = re.search(r'#.*[Uu]pdated[:\s]+(.+)', content)
            if updated_match:
                guidance.last_updated = updated_match.group(1).strip()
            
            # Parse each line
            for line in content.split('\n'):
                line = line.strip()
                
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue
                
                # Parse directives
                line_upper = line.upper()
                
                if line_upper.startswith('PRIORITY:'):
                    value = line[9:].strip()
                    if value:
                        guidance.priorities.append(value)
                
                elif line_upper.startswith('TRY:'):
                    value = line[4:].strip()
                    if value:
                        guidance.try_ideas.append(value)
                
                elif line_upper.startswith('AVOID:'):
                    value = line[6:].strip()
                    if value:
                        guidance.avoid.append(value)
                
                elif line_upper.startswith('FOCUS:'):
                    value = line[6:].strip()
                    if value:
                        guidance.focus.append(value)
                
                elif line_upper.startswith('NOTE:'):
                    value = line[5:].strip()
                    if value:
                        guidance.notes.append(value)
        
        except Exception as e:
            logger.warning(f"Error parsing guidance file: {e}")
        
        return guidance
    
    def get_prompt_text(self) -> str:
        """Get formatted guidance text for LLM prompt"""
        guidance = self.read_guidance()
        return guidance.to_prompt_text()


class HybridKnowledgeManager:
    """
    Manages knowledge from multiple sources.
    
    Sources:
    1. LLM's built-in knowledge (always available)
    2. Literature search (arXiv, Semantic Scholar) - triggered on plateau
    3. Web search (Gemini with Google Search) - triggered on plateau
    4. Human knowledge base (curated YAML)
    5. Human guidance (real-time txt file) - read every generation
    6. Kaggle notebooks - competition-winning techniques (NEW)
    7. Kaggle discussions - community insights (NEW)
    """
    
    def __init__(
        self,
        plateau_threshold: int = 10,
        stagnation_threshold: int = 3,
        periodic_interval: int = 30,
        min_generations: int = 20,
        search_cooldown: int = 15,
        human_kb_path: Optional[str] = None,
        human_guidance_path: Optional[str] = None,
        gemini_project_id: str = "prefab-root-439302-c5",
        gemini_location: str = "us-central1",
        kaggle_competition: Optional[str] = None,  # NEW: Kaggle competition slug
        kaggle_enabled: bool = True,  # NEW: Enable/disable Kaggle search
        llm_client=None,  # NEW: LLM client for technique analysis
        verbose: bool = True
    ):
        self.verbose = verbose
        self.kaggle_competition = kaggle_competition
        self.kaggle_enabled = kaggle_enabled and kaggle_competition is not None
        self.llm_client = llm_client
        
        # Initialize trigger
        self.trigger = NoveltySearchTrigger(
            plateau_threshold=plateau_threshold,
            stagnation_threshold=stagnation_threshold,
            periodic_interval=periodic_interval,
            min_generations=min_generations,
            search_cooldown=search_cooldown
        )
        
        # Initialize knowledge sources
        self.human_kb = HumanKnowledgeBase(human_kb_path)
        self.literature = LiteratureSearch(verbose=verbose)
        self.web = WebSearch(
            project_id=gemini_project_id,
            location=gemini_location,
            verbose=verbose
        )
        
        # Initialize literature search
        # Prefer full Kosmos integration if available, fallback to simple paper search
        self.kosmos_integration = None
        self.simple_paper_search = None
        
        if KOSMOS_INTEGRATION_AVAILABLE:
            try:
                self.kosmos_integration = KosmosLiteratureIntegration(
                    gemini_model='gemini-3-pro-preview',
                    enable_arxiv=True,
                    enable_semantic_scholar=True,
                    enable_pubmed=False,
                    verbose=verbose
                )
                if verbose:
                    print(f"   馃摎 Full Kosmos literature integration enabled (Gemini 3.0 Pro)")
            except Exception as e:
                print(f"   鈿狅笍 Kosmos integration failed: {e}, falling back to simple search")
                self.simple_paper_search = SimplePaperSearch(verbose=verbose) if SimplePaperSearch else None
        else:
            self.simple_paper_search = SimplePaperSearch(verbose=verbose) if SimplePaperSearch else None
        
        # Initialize human guidance reader (real-time steering)
        self.human_guidance = HumanGuidanceReader(
            guidance_file_path=human_guidance_path,
            verbose=verbose
        )
        
        # Initialize Kaggle sources (NEW)
        self.kaggle_notebook_client = None
        self.kaggle_discussion_scraper = None
        self.kaggle_analyzer = None
        
        if self.kaggle_enabled:
            if KAGGLE_CLIENT_AVAILABLE:
                try:
                    self.kaggle_notebook_client = KaggleNotebookClient()
                    logger.info("鉁?Kaggle Notebook Client initialized")
                except Exception as e:
                    logger.warning(f"鈿狅笍 Kaggle Notebook Client init failed: {e}")
            
            if KAGGLE_SCRAPER_AVAILABLE:
                try:
                    self.kaggle_discussion_scraper = KaggleDiscussionScraper(rate_limit=2.0)
                    logger.info("鉁?Kaggle Discussion Scraper initialized")
                except Exception as e:
                    logger.warning(f"鈿狅笍 Kaggle Discussion Scraper init failed: {e}")
            
            if KAGGLE_ANALYZER_AVAILABLE:
                try:
                    self.kaggle_analyzer = KaggleTechniqueAnalyzer(llm_client=llm_client)
                    logger.info("鉁?Kaggle Technique Analyzer initialized")
                except Exception as e:
                    logger.warning(f"鈿狅笍 Kaggle Technique Analyzer init failed: {e}")
        
        # Cache for recent searches
        self.cache: List[Technique] = []
        self.cached_abstracts: str = ""  # Cache for paper abstracts
        self.cached_kaggle_notebooks: List[Technique] = []  # NEW: Cache for Kaggle notebooks
        self.cached_kaggle_discussions: List[Technique] = []  # NEW: Cache for Kaggle discussions
        
        if self.verbose:
            print(f"馃摎 HybridKnowledgeManager initialized")
            print(f"   Plateau threshold: {plateau_threshold} gens")
            print(f"   Periodic search: every {periodic_interval} gens")
            print(f"   Literature: arXiv + Semantic Scholar")
            print(f"   Web: Gemini with Google Search grounding")
            print(f"   Kosmos Integration: {'鉁?Full (Gemini 3.0 Pro)' if self.kosmos_integration else '鉂?Disabled'}")
            print(f"   Simple Paper Search: {'鉁?Fallback' if self.simple_paper_search else '鉂?Disabled'}")
            print(f"   Kaggle Notebooks: {'鉁?Enabled' if self.kaggle_notebook_client else '鉂?Disabled'}")
            print(f"   Kaggle Discussions: {'鉁?Enabled' if self.kaggle_discussion_scraper else '鉂?Disabled'}")
            if kaggle_competition:
                print(f"   Kaggle Competition: {kaggle_competition}")
            if human_guidance_path:
                print(f"   Human guidance: {human_guidance_path}")
    
    @classmethod
    def from_config(cls, config, llm_client=None) -> 'HybridKnowledgeManager':
        """Create from KosmosConfig"""
        return cls(
            plateau_threshold=config.plateau_threshold,
            stagnation_threshold=config.stagnation_threshold,
            periodic_interval=config.periodic_search_interval,
            min_generations=config.min_generations_before_search,
            search_cooldown=config.search_cooldown,
            human_kb_path=config.human_kb_path,
            human_guidance_path=getattr(config, 'human_guidance_path', None),
            gemini_project_id=getattr(config, 'gemini_project_id', "prefab-root-439302-c5"),
            gemini_location=getattr(config, 'gemini_location', "us-central1"),
            kaggle_competition=getattr(config, 'kaggle_competition', None),
            kaggle_enabled=getattr(config, 'kaggle_enabled', True),
            llm_client=llm_client,
            verbose=True
        )
    
    def get_knowledge(
        self,
        task_description: str,
        evolution_history: List[Dict[str, Any]],
        current_gen: int
    ) -> KnowledgeBundle:
        """
        Get relevant knowledge for mutation.
        
        Args:
            task_description: Description of the task
            evolution_history: History of generations with scores
            current_gen: Current generation number
            
        Returns:
            KnowledgeBundle with techniques from all sources
        """
        bundle = KnowledgeBundle()
        
        # Always include human knowledge
        bundle.human_knowledge = self.human_kb.get_relevant(task_description)
        
        # Check if external search needed
        should_search, reason = self.trigger.should_search(current_gen, evolution_history)
        
        if should_search:
            if self.verbose:
                print(f"馃攳 Gen {current_gen}: External search triggered")
                print(f"   Reason: {reason}")
            
            # Build search query
            query = self._build_search_query(task_description)
            
            # Search literature (arXiv + Semantic Scholar)
            bundle.literature = self.literature.search(query)
            
            # Search web (Gemini with Google Search)
            bundle.web = self.web.search(query)
            
            # Get paper abstracts for direct LLM injection
            # Prefer full Kosmos integration (with concept extraction) over simple search
            if self.kosmos_integration:
                try:
                    search_result = self.kosmos_integration.search_and_extract(
                        query=query,
                        max_papers=5,
                        max_concepts_per_paper=5,
                        max_methods_per_paper=3
                    )
                    bundle.paper_abstracts = self.kosmos_integration.format_for_mutation_prompt(search_result)
                    self.cached_abstracts = bundle.paper_abstracts
                    if self.verbose:
                        print(f"   馃摎 Kosmos: {len(search_result.papers)} papers, {search_result.total_concepts} concepts, {search_result.total_methods} methods")
                except Exception as e:
                    if self.verbose:
                        print(f"   鈿狅笍 Kosmos search failed: {e}")
                    bundle.paper_abstracts = ""
            elif self.simple_paper_search:
                bundle.paper_abstracts = self.simple_paper_search.search_and_format(
                    query=query,
                    max_results=3,
                    task_description=task_description
                )
                self.cached_abstracts = bundle.paper_abstracts
                if self.verbose:
                    print(f"   馃搫 Paper abstracts (simple): {len(bundle.paper_abstracts)} chars")
            
            # NEW: Search Kaggle notebooks
            if self.kaggle_notebook_client and self.kaggle_competition:
                kaggle_nb_techniques = self._search_kaggle_notebooks()
                bundle.kaggle_notebooks = kaggle_nb_techniques
                self.cached_kaggle_notebooks = kaggle_nb_techniques
                if self.verbose:
                    print(f"   馃摀 Kaggle notebooks: {len(bundle.kaggle_notebooks)} techniques")
            
            # NEW: Search Kaggle discussions
            if self.kaggle_discussion_scraper and self.kaggle_competition:
                kaggle_disc_techniques = self._search_kaggle_discussions()
                bundle.kaggle_discussions = kaggle_disc_techniques
                self.cached_kaggle_discussions = kaggle_disc_techniques
                if self.verbose:
                    print(f"   馃挰 Kaggle discussions: {len(bundle.kaggle_discussions)} techniques")
            
            # Update cache
            self.cache = bundle.literature + bundle.web
            
            # Record search
            self.trigger.record_search(current_gen)
            
            bundle.search_performed = True
            bundle.search_reason = reason
            
            if self.verbose:
                print(f"   馃摎 Literature: {len(bundle.literature)} techniques")
                print(f"   馃寪 Web: {len(bundle.web)} techniques")
        else:
            # Use cached knowledge
            bundle.cached = self.cache
            bundle.paper_abstracts = self.cached_abstracts  # Use cached abstracts
            bundle.kaggle_notebooks = self.cached_kaggle_notebooks  # Use cached Kaggle
            bundle.kaggle_discussions = self.cached_kaggle_discussions
            bundle.search_performed = False
        
        return bundle
    
    def _search_kaggle_notebooks(self, max_notebooks: int = 5, max_techniques_per_nb: int = 5) -> List[Technique]:
        """
        Search Kaggle notebooks for the configured competition.
        
        Args:
            max_notebooks: Maximum notebooks to analyze
            max_techniques_per_nb: Maximum techniques to extract per notebook
        
        Returns:
            List of Technique objects
        """
        techniques = []
        
        if not self.kaggle_notebook_client or not self.kaggle_competition:
            return techniques
        
        try:
            # Search for top notebooks
            if self.verbose:
                logger.info(f"   馃攳 Searching Kaggle notebooks for '{self.kaggle_competition}'...")
            
            notebooks = self.kaggle_notebook_client.search_notebooks(
                competition=self.kaggle_competition,
                sort_by='voteCount',
                max_results=max_notebooks
            )
            
            if not notebooks:
                logger.info("   No Kaggle notebooks found")
                return techniques
            
            # Analyze each notebook
            for nb in notebooks[:max_notebooks]:
                try:
                    code = self.kaggle_notebook_client.download_notebook(nb.kernel_slug)
                    if not code:
                        continue
                    
                    # Extract techniques using analyzer
                    if self.kaggle_analyzer:
                        extracted = self.kaggle_analyzer.analyze_notebook(
                            code=code,
                            notebook_title=nb.title,
                            votes=nb.vote_count,
                            source_url=nb.url
                        )
                        
                        # Convert to Technique objects
                        for tech in extracted[:max_techniques_per_nb]:
                            techniques.append(Technique(
                                name=tech.name,
                                description=tech.description,
                                source='kaggle_notebook',
                                code_example=tech.code_snippet,
                                relevance_score=min(1.0, nb.vote_count / 100),
                                url=nb.url
                            ))
                    else:
                        # Basic technique extraction without analyzer
                        techniques.append(Technique(
                            name=f"Kaggle: {nb.title[:50]}",
                            description=f"Top-voted notebook ({nb.vote_count} votes). Review for techniques.",
                            source='kaggle_notebook',
                            relevance_score=min(1.0, nb.vote_count / 100),
                            url=nb.url
                        ))
                        
                except Exception as e:
                    logger.warning(f"   Error analyzing notebook {nb.kernel_slug}: {e}")
                    continue
            
            logger.info(f"   鉁?Extracted {len(techniques)} techniques from {len(notebooks)} notebooks")
            
        except Exception as e:
            logger.error(f"   鉂?Kaggle notebook search failed: {e}")
        
        return techniques
    
    def _search_kaggle_discussions(self, max_discussions: int = 10, max_techniques_per_disc: int = 5) -> List[Technique]:
        """
        Search Kaggle discussions for the configured competition.
        
        Args:
            max_discussions: Maximum discussions to analyze
            max_techniques_per_disc: Maximum techniques to extract per discussion
        
        Returns:
            List of Technique objects
        """
        techniques = []
        
        if not self.kaggle_discussion_scraper or not self.kaggle_competition:
            return techniques
        
        try:
            # Search for top discussions
            if self.verbose:
                logger.info(f"   馃攳 Searching Kaggle discussions for '{self.kaggle_competition}'...")
            
            discussions = self.kaggle_discussion_scraper.get_top_discussions(
                competition=self.kaggle_competition,
                max_results=max_discussions,
                sort_by='votes'
            )
            
            if not discussions:
                logger.info("   No Kaggle discussions found")
                return techniques
            
            # Analyze each discussion
            for disc in discussions[:max_discussions]:
                try:
                    content = self.kaggle_discussion_scraper.get_discussion_content(disc.url)
                    if not content:
                        continue
                    
                    # Extract insights using analyzer
                    if self.kaggle_analyzer:
                        extracted = self.kaggle_analyzer.analyze_discussion(
                            content=content,
                            title=disc.title,
                            votes=disc.vote_count,
                            source_url=disc.url
                        )
                        
                        # Convert to Technique objects
                        for tech in extracted[:max_techniques_per_disc]:
                            techniques.append(Technique(
                                name=tech.name,
                                description=tech.description,
                                source='kaggle_discussion',
                                code_example=tech.code_snippet,
                                relevance_score=min(1.0, disc.vote_count / 50),
                                url=disc.url
                            ))
                    else:
                        # Basic insight without analyzer
                        techniques.append(Technique(
                            name=f"Discussion: {disc.title[:50]}",
                            description=f"Top-voted discussion ({disc.vote_count} votes). Review for insights.",
                            source='kaggle_discussion',
                            relevance_score=min(1.0, disc.vote_count / 50),
                            url=disc.url
                        ))
                        
                except Exception as e:
                    logger.warning(f"   Error analyzing discussion {disc.id}: {e}")
                    continue
            
            logger.info(f"   鉁?Extracted {len(techniques)} insights from {len(discussions)} discussions")
            
        except Exception as e:
            logger.error(f"   鉂?Kaggle discussion search failed: {e}")
        
        return techniques
    
    def _build_search_query(self, task_description: str) -> str:
        """Build search query from task description"""
        # Extract key terms
        keywords = []
        
        # Common ML task indicators
        if 'classification' in task_description.lower():
            keywords.append('classification')
        if 'binary' in task_description.lower():
            keywords.append('binary')
        if 'imbalanced' in task_description.lower() or 'imbalance' in task_description.lower():
            keywords.append('imbalanced data')
        if 'f1' in task_description.lower():
            keywords.append('F1 score optimization')
        if 'regression' in task_description.lower():
            keywords.append('regression')
        if 'tabular' in task_description.lower():
            keywords.append('tabular data')
        if 'ctr' in task_description.lower() or 'click' in task_description.lower():
            keywords.append('CTR prediction')
        if 'embedding' in task_description.lower():
            keywords.append('embedding features')
        if 'lightgbm' in task_description.lower() or 'lgbm' in task_description.lower():
            keywords.append('gradient boosting')
        
        # Add year for recency
        keywords.append('2024 2025')
        keywords.append('state-of-the-art')
        
        return ' '.join(keywords) if keywords else task_description[:100]
    
    def format_for_mutation_prompt(self, bundle: KnowledgeBundle) -> str:
        """Format knowledge bundle for inclusion in mutation prompt"""
        
        all_techniques = bundle.all_techniques()
        
        if not all_techniques:
            return ""
        
        lines = [
            "",
            "鈺? * 60,
            "馃摎 EXTERNAL KNOWLEDGE (from real-time search)",
            "鈺? * 60,
        ]
        
        if bundle.search_performed:
            lines.append(f"Search triggered: {bundle.search_reason}")
            lines.append("")
        
        # Group by source
        by_source = {}
        for t in all_techniques:
            source = t.source
            if source not in by_source:
                by_source[source] = []
            by_source[source].append(t)
        
        source_names = {
            'human': '馃挕 EXPERT KNOWLEDGE (Curated)',
            'arxiv': '馃搫 FROM ARXIV PAPERS',
            'semantic_scholar': '馃摉 FROM SEMANTIC SCHOLAR',
            'web': '馃寪 FROM WEB SEARCH (Google)',
            'cached': '馃摝 CACHED KNOWLEDGE',
            'kaggle_notebook': '馃摀 FROM KAGGLE NOTEBOOKS',  # NEW
            'kaggle_discussion': '馃挰 FROM KAGGLE DISCUSSIONS',  # NEW
        }
        
        for source, techniques in by_source.items():
            lines.append(f"\n{source_names.get(source, source.upper())}:")
            
            for t in techniques[:8]:  # Max 8 per source (increased from 3)
                lines.append(f"鈥?{t.name}")
                lines.append(f"  {t.description[:200]}")
                if t.applicable_when:
                    lines.append(f"  When to use: {t.applicable_when}")
                if t.url:
                    lines.append(f"  Source: {t.url}")
                if t.code_example:
                    lines.append(f"  Example:")
                    lines.append(f"```python")
                    lines.append(t.code_example[:200])
                    lines.append(f"```")
        
        lines.append("")
        lines.append("Consider these techniques if relevant to the task!")
        lines.append("鈺? * 60)
        
        # NEW: Add paper abstracts if available
        if bundle.paper_abstracts:
            lines.append("")
            lines.append(bundle.paper_abstracts)
        
        return "\n".join(lines)
    
    def get_human_guidance_text(self) -> str:
        """Get formatted human guidance text for LLM prompt (read every call)"""
        return self.human_guidance.get_prompt_text()
    
    def get_full_knowledge_prompt(self, bundle: KnowledgeBundle) -> str:
        """
        Get combined knowledge prompt including:
        1. Human guidance (real-time)
        2. External knowledge (from search)
        
        Args:
            bundle: KnowledgeBundle from get_knowledge()
            
        Returns:
            Combined formatted text for LLM prompt
        """
        parts = []
        
        # Always include human guidance (read fresh every time)
        human_guidance_text = self.get_human_guidance_text()
        if human_guidance_text:
            parts.append(human_guidance_text)
        
        # Include external knowledge
        knowledge_text = self.format_for_mutation_prompt(bundle)
        if knowledge_text:
            parts.append(knowledge_text)
        
        return "\n".join(parts)
