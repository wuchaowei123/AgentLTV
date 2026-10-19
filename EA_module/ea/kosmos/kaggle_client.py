"""
Kaggle Client for notebooks and competition data.
Uses official Kaggle API for authorized access.

This module provides:
1. KaggleNotebookClient - Search and download Kaggle notebooks
2. KaggleNotebook - Dataclass for notebook metadata

Usage:
    client = KaggleNotebookClient()
    notebooks = client.search_notebooks('cafa-6-protein-function-prediction')
    for nb in notebooks[:3]:
        code = client.download_notebook(nb.kernel_slug)
        print(f"{nb.title}: {len(code)} chars")
"""

import os
import json
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class KaggleNotebook:
    """Metadata for a Kaggle notebook."""
    kernel_slug: str
    title: str
    author: str
    vote_count: int
    last_run_time: Optional[str]
    competition: str
    language: str  # python, r, etc.
    url: str
    code: Optional[str] = None
    outputs: Optional[List[str]] = None
    
    def to_dict(self) -> dict:
        return {
            'slug': self.kernel_slug,
            'title': self.title,
            'author': self.author,
            'votes': self.vote_count,
            'language': self.language,
            'url': self.url,
            'last_run': self.last_run_time,
        }
    
    def __repr__(self) -> str:
        return f"KaggleNotebook({self.title!r}, votes={self.vote_count})"


class KaggleNotebookClient:
    """
    Client for Kaggle notebooks using official API.
    
    Provides methods to:
    - Search notebooks by competition
    - Download notebook code
    - Cache downloaded notebooks
    
    Example:
        ```python
        client = KaggleNotebookClient()
        
        # Search top notebooks
        notebooks = client.search_notebooks(
            'cafa-6-protein-function-prediction',
            sort_by='voteCount',
            max_results=10
        )
        
        # Download and analyze top notebook
        for nb in notebooks[:3]:
            code = client.download_notebook(nb.kernel_slug)
            if code:
                print(f"Downloaded {nb.title}: {len(code)} chars")
        ```
    """
    
    def __init__(self, cache_dir: str = None):
        """
        Initialize Kaggle client.
        
        Args:
            cache_dir: Directory for caching downloaded notebooks.
                      Defaults to ./kaggle_cache in current working directory.
        """
        if cache_dir is None:
            cache_dir = './kaggle_cache'
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.api = None
        self._init_api()
    
    def _init_api(self):
        """Initialize Kaggle API with authentication."""
        try:
            from kaggle.api.kaggle_api_extended import KaggleApi
            self.api = KaggleApi()
            self.api.authenticate()
            logger.info("✅ Kaggle API authenticated successfully")
        except ImportError:
            logger.warning("⚠️ Kaggle package not installed. Install with: pip install kaggle")
            self.api = None
        except Exception as e:
            logger.error(f"❌ Kaggle API authentication failed: {e}")
            logger.info("   Ensure ~/.kaggle/kaggle.json exists or KAGGLE_API_TOKEN is set")
            self.api = None
    
    @property
    def is_available(self) -> bool:
        """Check if Kaggle API is available."""
        return self.api is not None
    
    def search_notebooks(
        self,
        competition: str,
        sort_by: str = 'voteCount',
        max_results: int = 20,
        language: str = 'python'
    ) -> List[KaggleNotebook]:
        """
        Search for top notebooks in a competition.
        
        Args:
            competition: Competition slug (e.g., 'cafa-6-protein-function-prediction')
            sort_by: Sorting criterion:
                - 'voteCount': Most upvoted (default)
                - 'dateCreated': Most recent
                - 'scoreAscending': Best scoring
                - 'scoreDescending': Worst scoring
            max_results: Maximum notebooks to return
            language: Filter by language ('python', 'r', 'all')
        
        Returns:
            List of KaggleNotebook objects sorted by the specified criterion
        """
        if not self.api:
            logger.warning("Kaggle API not available")
            return []
        
        try:
            # Build API call parameters
            params = {
                'competition': competition,
                'sort_by': sort_by,
                'page_size': min(max_results, 100),  # API limit
            }
            
            if language and language != 'all':
                params['language'] = language
            
            # Query API
            kernels = self.api.kernels_list(**params)
            
            # Parse results
            notebooks = []
            for k in kernels[:max_results]:
                nb = KaggleNotebook(
                    kernel_slug=k.ref,
                    title=k.title,
                    author=k.author,
                    vote_count=k.totalVotes,
                    last_run_time=str(k.lastRunTime) if hasattr(k, 'lastRunTime') and k.lastRunTime else None,
                    competition=competition,
                    language=language,
                    url=f"https://www.kaggle.com/code/{k.ref}"
                )
                notebooks.append(nb)
            
            logger.info(f"📓 Found {len(notebooks)} notebooks for '{competition}'")
            return notebooks
            
        except Exception as e:
            logger.error(f"Error searching notebooks: {e}")
            return []
    
    def search_notebooks_by_query(
        self,
        query: str,
        max_results: int = 20,
        sort_by: str = 'voteCount'
    ) -> List[KaggleNotebook]:
        """
        Search notebooks by keyword query (not competition-specific).
        
        Args:
            query: Search query (e.g., 'protein function prediction')
            max_results: Maximum notebooks to return
            sort_by: Sorting criterion
        
        Returns:
            List of KaggleNotebook objects
        """
        if not self.api:
            return []
        
        try:
            kernels = self.api.kernels_list(
                search=query,
                sort_by=sort_by,
                page_size=min(max_results, 100)
            )
            
            notebooks = []
            for k in kernels[:max_results]:
                nb = KaggleNotebook(
                    kernel_slug=k.ref,
                    title=k.title,
                    author=k.author,
                    vote_count=k.totalVotes,
                    last_run_time=str(k.lastRunTime) if hasattr(k, 'lastRunTime') and k.lastRunTime else None,
                    competition='',  # Not competition-specific
                    language='python',
                    url=f"https://www.kaggle.com/code/{k.ref}"
                )
                notebooks.append(nb)
            
            logger.info(f"📓 Found {len(notebooks)} notebooks for query '{query}'")
            return notebooks
            
        except Exception as e:
            logger.error(f"Error searching notebooks: {e}")
            return []
    
    def download_notebook(
        self,
        kernel_slug: str,
        force_refresh: bool = False
    ) -> Optional[str]:
        """
        Download notebook code.
        
        Downloads the notebook source code and caches it locally.
        Subsequent calls return cached version unless force_refresh=True.
        
        Args:
            kernel_slug: Notebook identifier (e.g., 'username/notebook-name')
            force_refresh: Re-download even if cached
        
        Returns:
            Notebook code as string, or None if download failed
        """
        # Normalize slug for cache filename
        cache_filename = kernel_slug.replace('/', '__') + '.py'
        cache_file = self.cache_dir / cache_filename
        
        # Return cached version if available
        if cache_file.exists() and not force_refresh:
            logger.debug(f"Using cached notebook: {cache_file}")
            return cache_file.read_text(encoding='utf-8')
        
        if not self.api:
            return None
        
        try:
            # Create temp directory for download
            temp_dir = self.cache_dir / 'temp'
            temp_dir.mkdir(exist_ok=True)
            
            # Clear temp directory
            for f in temp_dir.iterdir():
                if f.is_file():
                    f.unlink()
            
            # Download notebook
            logger.info(f"⬇️ Downloading notebook: {kernel_slug}")
            self.api.kernels_pull(kernel_slug, path=str(temp_dir), metadata=False)
            
            # Find and process downloaded file
            code = None
            for f in temp_dir.iterdir():
                if f.suffix in ['.py', '.ipynb']:
                    code = self._extract_code(f)
                    
                    # Cache the extracted code
                    if code:
                        cache_file.write_text(code, encoding='utf-8')
                        logger.info(f"✅ Cached notebook: {cache_file.name}")
                    
                    # Cleanup
                    f.unlink()
                    break
            
            return code
            
        except Exception as e:
            logger.error(f"Error downloading notebook {kernel_slug}: {e}")
            return None
    
    def _extract_code(self, filepath: Path) -> str:
        """
        Extract Python code from notebook or script.
        
        Args:
            filepath: Path to .py or .ipynb file
        
        Returns:
            Python code as string
        """
        if filepath.suffix == '.ipynb':
            # Parse Jupyter notebook
            try:
                with open(filepath, encoding='utf-8') as f:
                    nb_content = json.load(f)
                
                code_cells = []
                for cell in nb_content.get('cells', []):
                    if cell.get('cell_type') == 'code':
                        source = cell.get('source', [])
                        if isinstance(source, list):
                            code_cells.append(''.join(source))
                        else:
                            code_cells.append(source)
                
                # Join with cell separators for clarity
                return '\n\n# --- Cell ---\n\n'.join(code_cells)
                
            except json.JSONDecodeError as e:
                logger.error(f"Invalid notebook JSON: {e}")
                return ''
        else:
            # Plain Python script
            return filepath.read_text(encoding='utf-8')
    
    def get_notebook_metadata(self, kernel_slug: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed metadata for a notebook.
        
        Args:
            kernel_slug: Notebook identifier
        
        Returns:
            Dictionary with notebook metadata
        """
        if not self.api:
            return None
        
        try:
            # Create temp directory
            temp_dir = self.cache_dir / 'temp_meta'
            temp_dir.mkdir(exist_ok=True)
            
            # Download with metadata
            self.api.kernels_pull(kernel_slug, path=str(temp_dir), metadata=True)
            
            # Find metadata file
            meta_file = temp_dir / 'kernel-metadata.json'
            if meta_file.exists():
                with open(meta_file) as f:
                    return json.load(f)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting metadata for {kernel_slug}: {e}")
            return None
    
    def clear_cache(self):
        """Clear all cached notebooks."""
        import shutil
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info("🗑️ Cache cleared")


# Convenience function
def get_kaggle_client(cache_dir: str = None) -> KaggleNotebookClient:
    """Get a KaggleNotebookClient instance."""
    return KaggleNotebookClient(cache_dir=cache_dir)


if __name__ == "__main__":
    # Test the client
    logging.basicConfig(level=logging.INFO)
    
    client = KaggleNotebookClient()
    
    if client.is_available:
        print("\n=== Testing Kaggle Client ===\n")
        
        # Search notebooks
        notebooks = client.search_notebooks(
            'cafa-6-protein-function-prediction',
            max_results=5
        )
        
        print(f"Found {len(notebooks)} notebooks:\n")
        for i, nb in enumerate(notebooks, 1):
            print(f"{i}. {nb.title}")
            print(f"   Author: {nb.author}")
            print(f"   Votes: {nb.vote_count}")
            print(f"   URL: {nb.url}")
            print()
        
        # Download top notebook
        if notebooks:
            print(f"\nDownloading top notebook: {notebooks[0].title}")
            code = client.download_notebook(notebooks[0].kernel_slug)
            if code:
                print(f"Downloaded {len(code)} characters")
                print(f"\nFirst 500 chars:\n{code[:500]}...")
    else:
        print("Kaggle API not available. Please configure authentication.")

