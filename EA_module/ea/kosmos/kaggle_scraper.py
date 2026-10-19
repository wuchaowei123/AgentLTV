"""
Kaggle Discussion Scraper.
Extracts insights from competition discussions via web scraping.

Note: Use responsibly, respect rate limits and Kaggle's Terms of Service.
This module provides a best-effort approach to extracting discussion content.

Usage:
    scraper = KaggleDiscussionScraper()
    discussions = scraper.get_top_discussions('cafa-6-protein-function-prediction')
    
    for disc in discussions[:5]:
        content = scraper.get_discussion_content(disc.url)
        print(f"{disc.title}: {len(content) if content else 0} chars")
"""

import re
import time
import json
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin, quote

logger = logging.getLogger(__name__)

# Try to import requests and BeautifulSoup
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.warning("requests not installed. Install with: pip install requests")

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    logger.warning("BeautifulSoup not installed. Install with: pip install beautifulsoup4")


@dataclass
class KaggleDiscussion:
    """A Kaggle discussion thread."""
    id: str
    title: str
    author: str
    vote_count: int
    comment_count: int
    url: str
    content_preview: str
    tags: List[str] = field(default_factory=list)
    full_content: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'title': self.title,
            'author': self.author,
            'votes': self.vote_count,
            'comments': self.comment_count,
            'url': self.url,
            'preview': self.content_preview[:200] if self.content_preview else '',
            'tags': self.tags,
        }
    
    def __repr__(self) -> str:
        return f"KaggleDiscussion({self.title!r}, votes={self.vote_count})"


class KaggleDiscussionScraper:
    """
    Scraper for Kaggle discussions.
    
    Note: Kaggle uses a React-based frontend with dynamic loading.
    This scraper attempts to extract content but may need updates
    as Kaggle's website structure changes.
    
    For more reliable access, consider using Kaggle's official discussion
    API if/when it becomes available.
    
    Example:
        ```python
        scraper = KaggleDiscussionScraper(rate_limit=2.0)
        
        # Get top discussions
        discussions = scraper.get_top_discussions(
            'cafa-6-protein-function-prediction',
            max_results=10
        )
        
        # Get full content of interesting discussions
        for disc in discussions:
            if disc.vote_count > 10:
                content = scraper.get_discussion_content(disc.url)
                print(f"\\n=== {disc.title} ===\\n{content[:500]}...")
        ```
    """
    
    BASE_URL = "https://www.kaggle.com"
    COMPETITIONS_URL = f"{BASE_URL}/competitions"
    
    def __init__(
        self,
        rate_limit: float = 2.0,
        cache_dir: str = None,
        user_agent: str = None
    ):
        """
        Initialize scraper.
        
        Args:
            rate_limit: Minimum seconds between requests (be respectful!)
            cache_dir: Directory for caching scraped content
            user_agent: Custom user agent string
        """
        if not REQUESTS_AVAILABLE:
            raise ImportError("requests package required. Install with: pip install requests")
        
        self.rate_limit = rate_limit
        self.last_request_time = 0
        
        # Cache setup
        if cache_dir is None:
            cache_dir = './kaggle_discussion_cache'
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Session setup
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': user_agent or 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })
    
    def _rate_limited_request(
        self,
        url: str,
        method: str = 'GET',
        **kwargs
    ) -> Optional[requests.Response]:
        """
        Make rate-limited request.
        
        Args:
            url: URL to request
            method: HTTP method
            **kwargs: Additional arguments for requests
        
        Returns:
            Response object or None if failed
        """
        # Enforce rate limit
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit:
            sleep_time = self.rate_limit - elapsed
            logger.debug(f"Rate limiting: sleeping {sleep_time:.1f}s")
            time.sleep(sleep_time)
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, timeout=30, **kwargs)
            else:
                response = self.session.request(method, url, timeout=30, **kwargs)
            
            self.last_request_time = time.time()
            
            if response.status_code == 200:
                return response
            else:
                logger.warning(f"Request failed with status {response.status_code}: {url}")
                return None
                
        except requests.RequestException as e:
            logger.error(f"Request error: {e}")
            return None
    
    def get_top_discussions(
        self,
        competition: str,
        max_results: int = 20,
        sort_by: str = 'votes',
        use_cache: bool = True,
        cache_ttl: int = 3600  # Cache for 1 hour by default
    ) -> List[KaggleDiscussion]:
        """
        Get top discussions for a competition.
        
        Note: Due to Kaggle's dynamic loading, this may not capture all discussions.
        The method attempts multiple strategies to extract discussion data.
        
        Args:
            competition: Competition slug (e.g., 'cafa-6-protein-function-prediction')
            max_results: Maximum discussions to return
            sort_by: Sorting criterion ('votes', 'recent', 'comments')
            use_cache: Use cached discussion list if available
            cache_ttl: Cache time-to-live in seconds (default: 1 hour)
        
        Returns:
            List of KaggleDiscussion objects
        """
        # Check cache first
        cache_key = f"{competition}_{sort_by}_{max_results}"
        cache_file = self.cache_dir / f"discussions_{cache_key}.json"
        
        if use_cache and cache_file.exists():
            cache_age = time.time() - cache_file.stat().st_mtime
            if cache_age < cache_ttl:
                try:
                    with open(cache_file, 'r') as f:
                        cached_data = json.load(f)
                    discussions = [KaggleDiscussion(**d) for d in cached_data]
                    logger.info(f"📦 Using cached discussions for '{competition}' ({len(discussions)} items)")
                    return discussions
                except Exception as e:
                    logger.warning(f"Cache read failed: {e}")
        
        discussions = []
        
        # Strategy 1: Try the discussion list page
        url = f"{self.COMPETITIONS_URL}/{competition}/discussion"
        if sort_by == 'votes':
            url += "?sort=votes"
        elif sort_by == 'recent':
            url += "?sort=recent"
        elif sort_by == 'comments':
            url += "?sort=comments"
        
        response = self._rate_limited_request(url)
        if not response:
            logger.warning(f"Could not fetch discussions page for {competition}")
            return discussions
        
        # Strategy 2: Try to parse HTML
        if BS4_AVAILABLE:
            discussions.extend(self._parse_discussions_html(response.text, competition))
        
        # Strategy 3: Try to find embedded JSON data
        discussions.extend(self._extract_json_discussions(response.text, competition))
        
        # Deduplicate by ID
        seen_ids = set()
        unique_discussions = []
        for d in discussions:
            if d.id not in seen_ids:
                seen_ids.add(d.id)
                unique_discussions.append(d)
        
        # Sort by votes
        unique_discussions.sort(key=lambda x: x.vote_count, reverse=True)
        
        result = unique_discussions[:max_results]
        
        # Save to cache
        try:
            with open(cache_file, 'w') as f:
                json.dump([d.to_dict() for d in result], f)
            logger.info(f"💾 Cached {len(result)} discussions for '{competition}'")
        except Exception as e:
            logger.warning(f"Cache write failed: {e}")
        
        logger.info(f"💬 Found {len(result)} discussions for '{competition}'")
        return result
    
    def _parse_discussions_html(
        self,
        html: str,
        competition: str
    ) -> List[KaggleDiscussion]:
        """Parse discussions from HTML using BeautifulSoup."""
        if not BS4_AVAILABLE:
            return []
        
        discussions = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # Try various selectors (Kaggle's structure may change)
        selectors = [
            '.sc-hvvHee',  # Discussion list items (may change)
            '[data-testid="discussion-list-item"]',
            '.discussion-list-item',
            'div[class*="discussion"]',
        ]
        
        for selector in selectors:
            items = soup.select(selector)
            if items:
                for item in items:
                    disc = self._parse_discussion_element(item, competition)
                    if disc:
                        discussions.append(disc)
                if discussions:
                    break
        
        return discussions
    
    def _parse_discussion_element(
        self,
        element,
        competition: str
    ) -> Optional[KaggleDiscussion]:
        """Parse a single discussion element."""
        try:
            # Try to find title
            title_elem = (
                element.select_one('a[href*="/discussion/"]') or
                element.select_one('h3') or
                element.select_one('.title')
            )
            if not title_elem:
                return None
            
            title = title_elem.get_text(strip=True)
            
            # Try to find discussion ID from link
            link = title_elem.get('href', '')
            disc_id = ''
            if '/discussion/' in link:
                parts = link.split('/discussion/')
                if len(parts) > 1:
                    disc_id = parts[1].split('/')[0].split('?')[0]
            
            if not disc_id:
                disc_id = str(hash(title))[:8]
            
            # Try to find author
            author_elem = element.select_one('.author, [class*="author"]')
            author = author_elem.get_text(strip=True) if author_elem else 'Unknown'
            
            # Try to find vote count
            vote_elem = element.select_one('.vote-count, [class*="vote"]')
            vote_text = vote_elem.get_text(strip=True) if vote_elem else '0'
            try:
                votes = int(re.sub(r'[^\d]', '', vote_text) or '0')
            except ValueError:
                votes = 0
            
            # Build URL
            url = f"{self.COMPETITIONS_URL}/{competition}/discussion/{disc_id}"
            
            return KaggleDiscussion(
                id=disc_id,
                title=title,
                author=author,
                vote_count=votes,
                comment_count=0,
                url=url,
                content_preview=''
            )
            
        except Exception as e:
            logger.debug(f"Error parsing discussion element: {e}")
            return None
    
    def _extract_json_discussions(
        self,
        html: str,
        competition: str
    ) -> List[KaggleDiscussion]:
        """Try to extract discussions from embedded JSON data."""
        discussions = []
        
        # Look for JSON data in script tags
        patterns = [
            r'Kaggle\.State\.push\((.*?)\);',
            r'"discussions":\s*(\[.*?\])',
            r'window\.__PRELOADED_STATE__\s*=\s*({.*?});',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html, re.DOTALL)
            for match in matches:
                try:
                    data = json.loads(match)
                    if isinstance(data, list):
                        for item in data:
                            disc = self._parse_json_discussion(item, competition)
                            if disc:
                                discussions.append(disc)
                    elif isinstance(data, dict):
                        # Try to find discussions in nested structure
                        self._find_discussions_in_dict(data, discussions, competition)
                except json.JSONDecodeError:
                    continue
        
        return discussions
    
    def _find_discussions_in_dict(
        self,
        data: dict,
        discussions: List[KaggleDiscussion],
        competition: str
    ):
        """Recursively find discussions in a dictionary."""
        if 'discussions' in data and isinstance(data['discussions'], list):
            for item in data['discussions']:
                disc = self._parse_json_discussion(item, competition)
                if disc:
                    discussions.append(disc)
        
        for value in data.values():
            if isinstance(value, dict):
                self._find_discussions_in_dict(value, discussions, competition)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        self._find_discussions_in_dict(item, discussions, competition)
    
    def _parse_json_discussion(
        self,
        data: dict,
        competition: str
    ) -> Optional[KaggleDiscussion]:
        """Parse a discussion from JSON data."""
        try:
            # Try common field names
            disc_id = str(data.get('id', data.get('discussionId', data.get('topicId', ''))))
            title = data.get('title', data.get('name', ''))
            
            if not disc_id or not title:
                return None
            
            author = data.get('author', {})
            if isinstance(author, dict):
                author = author.get('displayName', author.get('name', 'Unknown'))
            
            return KaggleDiscussion(
                id=disc_id,
                title=title,
                author=str(author),
                vote_count=int(data.get('votes', data.get('voteCount', 0))),
                comment_count=int(data.get('commentCount', data.get('comments', 0))),
                url=f"{self.COMPETITIONS_URL}/{competition}/discussion/{disc_id}",
                content_preview=data.get('preview', data.get('excerpt', ''))[:500]
            )
        except Exception:
            return None
    
    def get_discussion_content(
        self,
        discussion_url: str,
        use_cache: bool = True
    ) -> Optional[str]:
        """
        Get full content of a discussion.
        
        Args:
            discussion_url: URL of the discussion
            use_cache: Use cached content if available
        
        Returns:
            Discussion content as string, or None if failed
        """
        # Check cache
        cache_key = quote(discussion_url, safe='')[:100]
        cache_file = self.cache_dir / f"{cache_key}.txt"
        
        if use_cache and cache_file.exists():
            return cache_file.read_text(encoding='utf-8')
        
        response = self._rate_limited_request(discussion_url)
        if not response:
            return None
        
        content = self._extract_discussion_content(response.text)
        
        if content:
            # Cache the content
            cache_file.write_text(content, encoding='utf-8')
        
        return content
    
    def _extract_discussion_content(self, html: str) -> Optional[str]:
        """Extract discussion content from HTML."""
        if not BS4_AVAILABLE:
            # Fallback: basic text extraction
            text = re.sub(r'<[^>]+>', ' ', html)
            text = re.sub(r'\s+', ' ', text)
            return text[:5000]
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove script and style elements
        for elem in soup(['script', 'style', 'nav', 'header', 'footer']):
            elem.decompose()
        
        # Try to find main content
        content_selectors = [
            '.discussion-content',
            '.markdown-body',
            '[class*="discussion-body"]',
            'article',
            'main',
        ]
        
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                text = content_elem.get_text(separator='\n', strip=True)
                if len(text) > 100:  # Minimum content length
                    return text
        
        # Fallback: get all text
        return soup.get_text(separator='\n', strip=True)[:10000]
    
    def clear_cache(self, competition: str = None):
        """
        Clear cached discussions.
        
        Args:
            competition: Optional competition slug. If None, clears all cache.
        """
        import shutil
        
        if competition:
            # Clear specific competition cache
            for f in self.cache_dir.glob(f"*{competition}*"):
                f.unlink()
            logger.info(f"🗑️ Cleared cache for '{competition}'")
        else:
            # Clear all cache
            if self.cache_dir.exists():
                shutil.rmtree(self.cache_dir)
                self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info("🗑️ Cleared all discussion cache")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = {
            'total_files': 0,
            'total_size_bytes': 0,
            'competitions': [],
        }
        
        if self.cache_dir.exists():
            for f in self.cache_dir.iterdir():
                if f.is_file():
                    stats['total_files'] += 1
                    stats['total_size_bytes'] += f.stat().st_size
                    # Extract competition name from filename
                    if f.name.startswith('discussions_'):
                        comp = f.name.replace('discussions_', '').split('_')[0]
                        if comp not in stats['competitions']:
                            stats['competitions'].append(comp)
        
        return stats
    
    def search_discussions(
        self,
        competition: str,
        query: str,
        max_results: int = 10
    ) -> List[KaggleDiscussion]:
        """
        Search discussions by keyword.
        
        Note: This filters the fetched discussions locally,
        as Kaggle doesn't provide a search API for discussions.
        
        Args:
            competition: Competition slug
            query: Search query
            max_results: Maximum results
        
        Returns:
            Filtered list of discussions
        """
        # Get all discussions first
        all_discussions = self.get_top_discussions(competition, max_results=50)
        
        # Filter by query
        query_lower = query.lower()
        filtered = [
            d for d in all_discussions
            if query_lower in d.title.lower() or query_lower in d.content_preview.lower()
        ]
        
        return filtered[:max_results]


# Convenience function
def get_discussion_scraper(rate_limit: float = 2.0) -> KaggleDiscussionScraper:
    """Get a KaggleDiscussionScraper instance."""
    return KaggleDiscussionScraper(rate_limit=rate_limit)


if __name__ == "__main__":
    # Test the scraper
    logging.basicConfig(level=logging.INFO)
    
    print("\n=== Testing Kaggle Discussion Scraper ===\n")
    
    scraper = KaggleDiscussionScraper(rate_limit=2.0)
    
    # Get discussions
    discussions = scraper.get_top_discussions(
        'cafa-6-protein-function-prediction',
        max_results=10
    )
    
    if discussions:
        print(f"Found {len(discussions)} discussions:\n")
        for i, disc in enumerate(discussions, 1):
            print(f"{i}. {disc.title}")
            print(f"   Author: {disc.author}")
            print(f"   Votes: {disc.vote_count}")
            print(f"   URL: {disc.url}")
            print()
        
        # Get content of top discussion
        if discussions:
            print(f"\nFetching content of: {discussions[0].title}")
            content = scraper.get_discussion_content(discussions[0].url)
            if content:
                print(f"Content length: {len(content)} chars")
                print(f"\nFirst 500 chars:\n{content[:500]}...")
    else:
        print("No discussions found. This may be due to:")
        print("- Kaggle's dynamic content loading")
        print("- Rate limiting")
        print("- Changed HTML structure")

