"""
Simple Paper Search for Evolution System

Instead of using LLM to analyze papers separately, we:
1. Search arXiv for relevant papers
2. Format abstracts directly for the mutation prompt
3. Let the evolution LLM use the abstracts as inspiration

This is simpler and more efficient than a separate analysis step.
"""

import re
import time
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import requests

logger = logging.getLogger(__name__)


@dataclass
class Paper:
    """A paper from arXiv"""
    title: str
    abstract: str
    url: str
    authors: Optional[str] = None
    published: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            'title': self.title,
            'abstract': self.abstract,
            'url': self.url,
            'authors': self.authors,
            'published': self.published,
        }


class SimplePaperSearch:
    """
    Simple arXiv search that returns papers directly.
    
    No LLM analysis - just fetch papers and format for prompt injection.
    The evolution LLM will use the abstracts as inspiration.
    """
    
    ARXIV_API_URL = "https://export.arxiv.org/api/query"
    
    # Rate limiting
    _last_request_time = 0.0
    _min_request_interval = 3.0
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
    
    def search(
        self,
        query: str,
        max_results: int = 5
    ) -> List[Paper]:
        """
        Search arXiv for papers.
        
        Args:
            query: Search query (e.g., "CTR prediction deep learning")
            max_results: Maximum papers to return
            
        Returns:
            List of Paper objects
        """
        if self.verbose:
            logger.info(f"📚 Searching arXiv: {query[:50]}...")
        
        # Build query
        query_words = query.split()[:7]  # Use more words for better results
        arxiv_query = ' '.join(query_words)
        
        params = {
            'search_query': f'all:{arxiv_query}',
            'start': 0,
            'max_results': max_results,
            'sortBy': 'relevance',
            'sortOrder': 'descending'
        }
        
        # Respect rate limiting
        time_since_last = time.time() - SimplePaperSearch._last_request_time
        if time_since_last < SimplePaperSearch._min_request_interval:
            wait_time = SimplePaperSearch._min_request_interval - time_since_last
            time.sleep(wait_time)
        
        try:
            SimplePaperSearch._last_request_time = time.time()
            response = requests.get(self.ARXIV_API_URL, params=params, timeout=60)
            response.raise_for_status()
            papers = self._parse_arxiv_xml(response.text)
            
            if self.verbose:
                logger.info(f"   Found {len(papers)} papers")
            
            return papers
            
        except Exception as e:
            logger.warning(f"arXiv search failed: {e}")
            return []
    
    def _parse_arxiv_xml(self, xml_text: str) -> List[Paper]:
        """Parse arXiv XML response"""
        import xml.etree.ElementTree as ET
        
        papers = []
        try:
            root = ET.fromstring(xml_text)
            ns = {
                'atom': 'http://www.w3.org/2005/Atom',
                'arxiv': 'http://arxiv.org/schemas/atom'
            }
            
            for entry in root.findall('atom:entry', ns):
                title = entry.find('atom:title', ns)
                summary = entry.find('atom:summary', ns)
                link = entry.find("atom:link[@type='text/html']", ns)
                published = entry.find('atom:published', ns)
                
                # Get authors
                authors = []
                for author in entry.findall('atom:author', ns):
                    name = author.find('atom:name', ns)
                    if name is not None:
                        authors.append(name.text)
                
                if title is not None and summary is not None:
                    papers.append(Paper(
                        title=title.text.strip().replace('\n', ' '),
                        abstract=summary.text.strip().replace('\n', ' '),
                        url=link.get('href') if link is not None else '',
                        authors=', '.join(authors[:3]) + ('...' if len(authors) > 3 else ''),
                        published=published.text[:10] if published is not None else None
                    ))
        except Exception as e:
            logger.warning(f"XML parse error: {e}")
        
        return papers
    
    def format_for_prompt(
        self,
        papers: List[Paper],
        task_description: str = "",
        max_abstract_length: int = 500
    ) -> str:
        """
        Format papers for direct injection into mutation prompt.
        
        Args:
            papers: List of papers to format
            task_description: Optional task context
            max_abstract_length: Truncate abstracts to this length
            
        Returns:
            Formatted string for prompt injection
        """
        if not papers:
            return ""
        
        lines = [
            "",
            "═" * 60,
            "📚 RELEVANT RESEARCH PAPERS (from arXiv)",
            "═" * 60,
            "",
            "The following papers contain methods that may help improve your solution.",
            "Read the abstracts and consider implementing relevant techniques.",
            "",
        ]
        
        for i, paper in enumerate(papers, 1):
            # Truncate abstract if needed
            abstract = paper.abstract
            if len(abstract) > max_abstract_length:
                abstract = abstract[:max_abstract_length] + "..."
            
            lines.append(f"### Paper {i}: {paper.title}")
            if paper.published:
                lines.append(f"**Published:** {paper.published}")
            lines.append(f"**URL:** {paper.url}")
            lines.append("")
            lines.append(f"**Abstract:** {abstract}")
            lines.append("")
            lines.append("-" * 40)
            lines.append("")
        
        lines.append("═" * 60)
        lines.append("Consider implementing techniques from these papers!")
        lines.append("═" * 60)
        
        return "\n".join(lines)
    
    def search_and_format(
        self,
        query: str,
        max_results: int = 3,
        task_description: str = ""
    ) -> str:
        """
        Search arXiv and format results for prompt injection.
        
        Args:
            query: Search query
            max_results: Maximum papers
            task_description: Optional task context
            
        Returns:
            Formatted string ready for prompt injection
        """
        papers = self.search(query, max_results)
        return self.format_for_prompt(papers, task_description)


def test_simple_search():
    """Test the simple paper search"""
    print("=" * 70)
    print("SIMPLE PAPER SEARCH TEST")
    print("=" * 70)
    
    search = SimplePaperSearch(verbose=True)
    
    # Test search
    query = "click-through rate prediction deep learning"
    papers = search.search(query, max_results=3)
    
    print(f"\n✅ Found {len(papers)} papers:\n")
    for i, p in enumerate(papers, 1):
        print(f"{i}. {p.title[:60]}...")
        print(f"   URL: {p.url}")
        print(f"   Abstract: {p.abstract[:100]}...")
        print()
    
    print("=" * 70)
    print("FORMATTED OUTPUT FOR PROMPT:")
    print("=" * 70)
    formatted = search.format_for_prompt(papers)
    print(formatted)


if __name__ == "__main__":
    test_simple_search()

