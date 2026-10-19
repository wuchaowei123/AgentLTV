"""
Gemini-powered concept and method extraction from scientific papers.

Uses Gemini 3.0 Pro to extract structured information including:
- Scientific concepts and their relationships
- Methods and techniques used
- Relevance scores and context
- Step-by-step implementation details from FULL PDF

Enhanced to support DIRECT PDF upload to Gemini API (recommended) 
or fallback to text extraction via PyMuPDF.
"""

import json
import logging
import hashlib
import time
import re
import requests
import os
from typing import List, Dict, Any, Optional, Set, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

# Try to import Google GenAI for direct PDF upload
try:
    from google import genai
    from google.genai import types
    GOOGLE_GENAI_AVAILABLE = True
except ImportError:
    GOOGLE_GENAI_AVAILABLE = False
    logger.info("google-genai not available, will use fallback text extraction")

# Try to import PyMuPDF for PDF extraction (fallback)
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    logger.info("PyMuPDF not available, PDF text extraction disabled")


# =============================================================================
# DATA CLASSES (Same structure as Kosmos)
# =============================================================================

@dataclass
class ExtractedConcept:
    """Represents an extracted scientific concept."""
    name: str
    description: str
    domain: str
    relevance: float  # 0-1 score

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExtractedMethod:
    """Represents an extracted method or technique with implementation details."""
    name: str
    description: str
    category: str  # loss_function, architecture, training_strategy, etc.
    confidence: float  # 0-1 score
    implementation_hints: List[str] = None  # NEW: Bullet points for implementation
    code_snippet: str = ""  # NEW: Python code snippet

    def __post_init__(self):
        if self.implementation_hints is None:
            self.implementation_hints = []

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ConceptRelationship:
    """Represents a relationship between concepts."""
    concept1: str
    concept2: str
    relationship_type: str  # SUBTOPIC_OF, RELATED_TO, PREREQUISITE_FOR, etc.
    strength: float  # 0-1 score

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExtractionResult:
    """Complete extraction result for a paper."""
    paper_id: str
    concepts: List[ExtractedConcept]
    methods: List[ExtractedMethod]
    relationships: List[ConceptRelationship]
    extraction_time: float
    model_used: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "paper_id": self.paper_id,
            "concepts": [c.to_dict() for c in self.concepts],
            "methods": [m.to_dict() for m in self.methods],
            "relationships": [r.to_dict() for r in self.relationships],
            "extraction_time": self.extraction_time,
            "model_used": self.model_used
        }


# =============================================================================
# SIMPLE PAPER METADATA (for compatibility)
# =============================================================================

@dataclass
class PaperMetadata:
    """Simple paper metadata (compatible with Kosmos)."""
    title: str
    abstract: str
    url: str
    id: str = ""
    primary_identifier: str = ""
    doi: str = ""
    arxiv_id: str = ""
    pubmed_id: str = ""
    authors: List[str] = None
    published: str = ""
    full_text: str = ""
    source: str = "unknown"

    def __post_init__(self):
        if not self.id:
            self.id = hashlib.md5(self.title.encode()).hexdigest()[:12]
        if not self.primary_identifier:
            self.primary_identifier = self.doi or self.arxiv_id or self.id
        if self.authors is None:
            self.authors = []


# =============================================================================
# GEMINI CONCEPT EXTRACTOR
# =============================================================================

class GeminiConceptExtractor:
    """
    Gemini-powered extractor for scientific concepts and methods.

    Supports TWO modes for PDF analysis:
    1. DIRECT PDF UPLOAD (recommended): Uses Gemini's native PDF understanding
    2. TEXT EXTRACTION (fallback): Uses PyMuPDF to extract text, then sends to LLM
    
    Direct PDF upload is preferred as Gemini can see figures, tables, and formatting.
    """

    def __init__(
        self,
        model: str = "gemini-2.5-flash",  # Use flash for faster processing
        cache_dir: Optional[str] = None,
        use_cache: bool = True,
        max_tokens: int = 16000,  # Increased for detailed extraction with code
        temperature: float = 0.0,
        verbose: bool = True,
        use_direct_pdf: bool = True,  # NEW: Prefer direct PDF upload to Gemini
        google_api_key: Optional[str] = None  # API key for google-genai
    ):
        """
        Initialize Gemini concept extractor.

        Args:
            model: Gemini model to use (default: gemini-2.5-flash)
            cache_dir: Cache directory for extractions
            use_cache: Whether to use caching
            max_tokens: Maximum tokens for response
            temperature: Sampling temperature (0 for deterministic)
            verbose: Print progress messages
            use_direct_pdf: Whether to upload PDFs directly to Gemini (recommended)
            google_api_key: API key for google-genai (falls back to GOOGLE_API_KEY env var)
        """
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.verbose = verbose
        self.use_direct_pdf = use_direct_pdf and GOOGLE_GENAI_AVAILABLE
        
        # Initialize Google GenAI client for direct PDF upload
        self.genai_client = None
        if self.use_direct_pdf:
            try:
                api_key = google_api_key or os.environ.get('GOOGLE_API_KEY')
                project = os.environ.get('GOOGLE_CLOUD_PROJECT', 'prefab-root-439302-c5')
                location = os.environ.get('GOOGLE_CLOUD_LOCATION', 'us-central1')
                
                if api_key:
                    # Use Google AI API with API key
                    self.genai_client = genai.Client(api_key=api_key)
                    if verbose:
                        logger.info("閴?Google GenAI client initialized with API key")
                else:
                    # Use Vertex AI (GCP environment)
                    self.genai_client = genai.Client(
                        vertexai=True,
                        project=project,
                        location=location
                    )
                    if verbose:
                        logger.info(f"閴?Google GenAI client initialized with Vertex AI (project={project})")
            except Exception as e:
                logger.warning(f"Failed to init Google GenAI client: {e}")
                self.genai_client = None
                self.use_direct_pdf = False

        # Initialize LLM client (fallback for text-based extraction)
        self.llm_client = None
        if not self.use_direct_pdf:
            try:
                from ea.llm.llm import LLMClient
                self.llm_client = LLMClient(
                    model_names=[model],
                    max_tokens=max_tokens,
                    temperatures=temperature,
                )
            except ImportError:
                logger.warning("AgentLTV LLM client not available, using litellm directly")

        # Caching setup
        self.use_cache = use_cache
        if use_cache:
            self.cache_dir = Path(cache_dir or ".concept_extraction_cache")
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.cache_dir = None

        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1.0  # seconds between requests
        
        # PDF cache directory
        self.pdf_cache_dir = Path(cache_dir or ".pdf_cache") if cache_dir else Path(".pdf_cache")
        self.pdf_cache_dir.mkdir(parents=True, exist_ok=True)

        if verbose:
            logger.info(f"Initialized GeminiConceptExtractor (model={model})")
            logger.info(f"   Direct PDF upload: {'閴?Enabled' if self.use_direct_pdf else '閴?Disabled'}")
            logger.info(f"   Text extraction fallback: {'閴?Available' if PYMUPDF_AVAILABLE else '閴?Not available'}")
    
    # =========================================================================
    # PDF EXTRACTION METHODS
    # =========================================================================
    
    def _get_arxiv_pdf_url(self, paper: PaperMetadata) -> Optional[str]:
        """Get the PDF URL for an arXiv paper."""
        # Try to extract arXiv ID from URL or arxiv_id field
        arxiv_id = paper.arxiv_id
        
        if not arxiv_id and paper.url:
            # Try to extract from URL like https://arxiv.org/abs/2103.00020
            match = re.search(r'arxiv.org/abs/(\d+\.\d+)', paper.url)
            if match:
                arxiv_id = match.group(1)
        
        if arxiv_id:
            return f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        
        return None
    
    def _download_pdf(self, url: str, paper_id: str) -> Optional[Path]:
        """Download a PDF and cache it locally."""
        cache_path = self.pdf_cache_dir / f"{paper_id}.pdf"
        
        # Check cache
        if cache_path.exists():
            if self.verbose:
                logger.info(f"   Using cached PDF: {cache_path}")
            return cache_path
        
        # Download
        try:
            if self.verbose:
                logger.info(f"   Downloading PDF from {url[:50]}...")
            
            response = requests.get(url, timeout=60, stream=True)
            response.raise_for_status()
            
            # Check if it's actually a PDF
            content_type = response.headers.get('content-type', '')
            if 'pdf' not in content_type.lower() and not response.content[:4] == b'%PDF':
                logger.warning(f"   Not a PDF: {content_type}")
                return None
            
            # Save to cache
            with open(cache_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            if self.verbose:
                logger.info(f"   Downloaded PDF: {cache_path} ({cache_path.stat().st_size / 1024:.1f} KB)")
            
            return cache_path
        except Exception as e:
            logger.warning(f"   PDF download failed: {e}")
            return None
    
    def _extract_text_from_pdf(self, pdf_path: Path, max_chars: int = 30000) -> Optional[str]:
        """Extract text from a PDF file using PyMuPDF."""
        if not PYMUPDF_AVAILABLE:
            logger.warning("   PyMuPDF not available, cannot extract PDF text")
            return None
        
        try:
            doc = fitz.open(str(pdf_path))
            text_parts = []
            total_chars = 0
            
            for page_num, page in enumerate(doc):
                page_text = page.get_text()
                text_parts.append(f"\n--- Page {page_num + 1} ---\n{page_text}")
                total_chars += len(page_text)
                
                if total_chars > max_chars:
                    break
            
            doc.close()
            
            full_text = "\n".join(text_parts)[:max_chars]
            
            if self.verbose:
                logger.info(f"   Extracted {len(full_text)} chars from PDF ({page_num + 1} pages)")
            
            return full_text
        except Exception as e:
            logger.warning(f"   PDF text extraction failed: {e}")
            return None
    
    def _get_full_paper_text(self, paper: PaperMetadata, max_chars: int = 20000) -> str:
        """
        Get the full text of a paper, preferring PDF extraction over abstract.
        
        Returns:
            Full paper text (from PDF) or abstract (fallback)
        """
        # Try PDF extraction first
        if PYMUPDF_AVAILABLE:
            pdf_url = self._get_arxiv_pdf_url(paper)
            if pdf_url:
                pdf_path = self._download_pdf(pdf_url, paper.primary_identifier)
                if pdf_path:
                    full_text = self._extract_text_from_pdf(pdf_path, max_chars)
                    if full_text and len(full_text) > 500:
                        return full_text
        
        # Fallback to stored full_text
        if paper.full_text and len(paper.full_text) > 500:
            return paper.full_text[:max_chars]
        
        # Fallback to abstract
        if paper.abstract:
            return paper.abstract
        
        return "No text available"

    def _rate_limit(self):
        """Apply rate limiting between requests."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()

    def _upload_to_gcs(self, pdf_path: Path, bucket_name: str = "avia_test_bucket_harry") -> Optional[str]:
        """
        Upload PDF to Google Cloud Storage for Vertex AI access.
        
        Args:
            pdf_path: Local path to PDF file
            bucket_name: GCS bucket name
            
        Returns:
            GCS URI (gs://bucket/path) or None if failed
        """
        import subprocess
        
        gcs_path = f"gs://{bucket_name}/pdf_cache/{pdf_path.name}"
        
        try:
            # Check if already uploaded
            check_cmd = ["gsutil", "ls", gcs_path]
            result = subprocess.run(check_cmd, capture_output=True, text=True)
            if result.returncode == 0:
                if self.verbose:
                    logger.info(f"   PDF already in GCS: {gcs_path}")
                return gcs_path
            
            # Upload to GCS
            if self.verbose:
                logger.info(f"   Uploading PDF to GCS: {gcs_path}...")
            
            upload_cmd = ["gsutil", "cp", str(pdf_path), gcs_path]
            result = subprocess.run(upload_cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                if self.verbose:
                    logger.info(f"   閴?PDF uploaded to GCS")
                return gcs_path
            else:
                logger.error(f"   GCS upload failed: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"   GCS upload error: {e}")
            return None

    def _call_gemini_with_pdf(self, pdf_path: Path, prompt: str) -> str:
        """
        Call Gemini API directly with a PDF file via GCS.
        
        This is the PREFERRED method as Gemini can see figures, tables, and formatting.
        
        For Vertex AI: Uploads PDF to GCS first, then references it.
        For Google AI API: Uploads directly via files.upload().
        
        Args:
            pdf_path: Path to the PDF file
            prompt: The prompt to send with the PDF
            
        Returns:
            Response text from Gemini
        """
        if not self.genai_client:
            logger.warning("Google GenAI client not available")
            return ""
        
        self._rate_limit()
        
        try:
            pdf_size_kb = pdf_path.stat().st_size / 1024
            if self.verbose:
                logger.info(f"   Processing PDF ({pdf_size_kb:.1f} KB)...")
            
            # Try direct upload first (works with Google AI API key)
            try:
                with open(pdf_path, 'rb') as f:
                    pdf_data = f.read()
                
                uploaded_file = self.genai_client.files.upload(
                    file=pdf_data,
                    config=types.UploadFileConfig(
                        mime_type='application/pdf',
                        display_name=pdf_path.name
                    )
                )
                
                if self.verbose:
                    logger.info(f"   閴?PDF uploaded directly: {uploaded_file.name}")
                
                # Generate content with the uploaded file
                response = self.genai_client.models.generate_content(
                    model=self.model,
                    contents=[uploaded_file, prompt],
                    config=types.GenerateContentConfig(
                        max_output_tokens=self.max_tokens,
                        temperature=self.temperature,
                    )
                )
                
                # Cleanup
                try:
                    self.genai_client.files.delete(name=uploaded_file.name)
                except:
                    pass
                
                if response and response.text:
                    return response.text
                    
            except Exception as e:
                if "Vertex AI does not support" in str(e):
                    # Vertex AI - use GCS approach
                    if self.verbose:
                        logger.info("   Using GCS upload for Vertex AI...")
                    
                    gcs_uri = self._upload_to_gcs(pdf_path)
                    if gcs_uri:
                        # Create Part from GCS URI
                        file_part = types.Part.from_uri(
                            file_uri=gcs_uri,
                            mime_type="application/pdf"
                        )
                        
                        response = self.genai_client.models.generate_content(
                            model=self.model,
                            contents=[file_part, prompt],
                            config=types.GenerateContentConfig(
                                max_output_tokens=self.max_tokens,
                                temperature=self.temperature,
                            )
                        )
                        
                        if response and response.text:
                            if self.verbose:
                                logger.info("   閴?Generated content from GCS PDF")
                            return response.text
                else:
                    raise e
            
            logger.warning("Empty response from Gemini")
            return ""
                
        except Exception as e:
            logger.error(f"Gemini PDF API error: {e}")
            return ""

    def _get_cache_path(self, paper_id: str) -> Path:
        """Get cache file path for a paper."""
        safe_id = hashlib.md5(paper_id.encode()).hexdigest()
        return self.cache_dir / f"{safe_id}.json"

    def _get_from_cache(self, paper_id: str) -> Optional[ExtractionResult]:
        """Get extraction result from cache."""
        if not self.use_cache or not self.cache_dir:
            return None

        cache_path = self._get_cache_path(paper_id)
        if not cache_path.exists():
            return None

        try:
            with open(cache_path, 'r') as f:
                data = json.load(f)

            return ExtractionResult(
                paper_id=data["paper_id"],
                concepts=[ExtractedConcept(**c) for c in data["concepts"]],
                methods=[ExtractedMethod(**m) for m in data["methods"]],
                relationships=[ConceptRelationship(**r) for r in data["relationships"]],
                extraction_time=data["extraction_time"],
                model_used=data["model_used"]
            )
        except Exception as e:
            logger.warning(f"Cache read error for {paper_id}: {e}")
            return None

    def _save_to_cache(self, paper_id: str, result: ExtractionResult):
        """Save extraction result to cache."""
        if not self.use_cache or not self.cache_dir:
            return

        cache_path = self._get_cache_path(paper_id)
        try:
            with open(cache_path, 'w') as f:
                json.dump(result.to_dict(), f, indent=2)
        except Exception as e:
            logger.warning(f"Cache write error for {paper_id}: {e}")

    def _call_llm(self, prompt: str, system_msg: str = "") -> str:
        """Call LLM and return response text."""
        self._rate_limit()

        if self.llm_client:
            try:
                result = self.llm_client.query(msg=prompt, system_msg=system_msg)
                if result and result.content:
                    return result.content
            except Exception as e:
                logger.error(f"LLM client error: {e}")

        # Fallback to direct litellm
        try:
            import litellm
            response = litellm.completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_msg} if system_msg else {},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"litellm error: {e}")
            return ""

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON from LLM response."""
        # Try to extract JSON from response
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try direct JSON parse
        try:
            # Find JSON object in response
            start = response.find('{')
            end = response.rfind('}') + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
        except json.JSONDecodeError:
            pass

        logger.warning("Could not parse JSON from LLM response")
        return {}

    def extract_from_paper(
        self,
        paper: PaperMetadata,
        include_relationships: bool = True,
        max_concepts: int = 10,
        max_methods: int = 5
    ) -> ExtractionResult:
        """
        Extract concepts and methods from a paper.

        Args:
            paper: PaperMetadata object
            include_relationships: Whether to extract concept relationships
            max_concepts: Maximum number of concepts to extract
            max_methods: Maximum number of methods to extract

        Returns:
            ExtractionResult with concepts, methods, and relationships
        """
        # Check cache
        if self.use_cache:
            cached = self._get_from_cache(paper.primary_identifier)
            if cached:
                if self.verbose:
                    logger.info(f"Using cached extraction for {paper.primary_identifier}")
                return cached

        start_time = time.time()

        if self.verbose:
            logger.info(f"Extracting concepts from: {paper.title[:60]}...")

        # Extract concepts and methods
        concepts_and_methods = self._extract_concepts_and_methods(
            paper,
            max_concepts=max_concepts,
            max_methods=max_methods
        )

        concepts = concepts_and_methods.get("concepts", [])
        methods = concepts_and_methods.get("methods", [])

        # Extract relationships if requested
        relationships = []
        if include_relationships and len(concepts) > 1:
            relationships = self._extract_relationships(paper, concepts)

        extraction_time = time.time() - start_time

        result = ExtractionResult(
            paper_id=paper.primary_identifier,
            concepts=concepts,
            methods=methods,
            relationships=relationships,
            extraction_time=extraction_time,
            model_used=self.model
        )

        # Cache result
        if self.use_cache:
            self._save_to_cache(paper.primary_identifier, result)

        if self.verbose:
            logger.info(
                f"Extracted {len(concepts)} concepts, {len(methods)} methods "
                f"in {extraction_time:.2f}s"
            )

        return result

    def extract_from_papers(
        self,
        papers: List[PaperMetadata],
        show_progress: bool = True
    ) -> List[ExtractionResult]:
        """
        Extract from multiple papers (batch processing).

        Args:
            papers: List of papers
            show_progress: Whether to show progress

        Returns:
            List of extraction results
        """
        results = []

        for i, paper in enumerate(papers):
            if show_progress:
                logger.info(f"Processing paper {i + 1}/{len(papers)}: {paper.title[:50]}...")

            try:
                result = self.extract_from_paper(paper)
                results.append(result)
            except Exception as e:
                logger.error(f"Error extracting from paper {paper.primary_identifier}: {e}")
                results.append(ExtractionResult(
                    paper_id=paper.primary_identifier,
                    concepts=[],
                    methods=[],
                    relationships=[],
                    extraction_time=0.0,
                    model_used=self.model
                ))

        return results

    def _extract_concepts_and_methods(
        self,
        paper: PaperMetadata,
        max_concepts: int,
        max_methods: int
    ) -> Dict[str, Any]:
        """
        Extract concepts and methods using Gemini.
        
        Prefers DIRECT PDF upload to Gemini (can see figures/tables),
        falls back to text extraction if not available.

        Args:
            paper: Paper metadata
            max_concepts: Maximum concepts
            max_methods: Maximum methods

        Returns:
            Dictionary with concepts and methods lists
        """
        response_text = ""
        
        # Try direct PDF upload first (PREFERRED - Gemini can see figures/tables)
        if self.use_direct_pdf and self.genai_client:
            pdf_url = self._get_arxiv_pdf_url(paper)
            if pdf_url:
                pdf_path = self._download_pdf(pdf_url, paper.primary_identifier)
                if pdf_path and pdf_path.exists():
                    prompt = self._build_pdf_extraction_prompt(
                        paper.title,
                        max_concepts=max_concepts,
                        max_methods=max_methods
                    )
                    response_text = self._call_gemini_with_pdf(pdf_path, prompt)
                    
                    if response_text:
                        if self.verbose:
                            logger.info("   閴?Used direct PDF upload to Gemini")
        
        # Fallback to text extraction
        if not response_text:
            if self.verbose:
                logger.info("   棣冩惈 Using text extraction fallback...")
            
            prompt = self._build_concept_extraction_prompt(
                paper,
                max_concepts=max_concepts,
                max_methods=max_methods
            )

            response_text = self._call_llm(
                prompt,
                system_msg="You are a scientific literature analyst specializing in extracting key concepts and methods from research papers."
            )

        if not response_text:
            return {"concepts": [], "methods": []}

        parsed = self._parse_json_response(response_text)

        # Convert to dataclasses
        concepts = [
            ExtractedConcept(
                name=c.get("name", "Unknown"),
                description=c.get("description", ""),
                domain=c.get("domain", "unknown"),
                relevance=c.get("relevance", 0.5)
            )
            for c in parsed.get("concepts", [])
        ]

        methods = [
            ExtractedMethod(
                name=m.get("name", "Unknown"),
                description=m.get("description", ""),
                category=m.get("category", "unknown"),
                confidence=m.get("confidence", 0.5),
                implementation_hints=m.get("implementation_hints", []),
                code_snippet=m.get("code_snippet", "")
            )
            for m in parsed.get("methods", [])
        ]

        return {"concepts": concepts, "methods": methods}
    
    def _build_pdf_extraction_prompt(
        self,
        paper_title: str,
        max_concepts: int,
        max_methods: int
    ) -> str:
        """Build prompt for direct PDF analysis (Gemini can see the full PDF)."""
        return f"""You are a senior ML research engineer specializing in implementing techniques from scientific papers.

I'm sharing a PDF of the paper titled: "{paper_title}"

**IMPORTANT: You can see the ENTIRE PDF including figures, tables, equations, and formatting. Use ALL of this information.**

Your task: Extract {max_concepts} key concepts and {max_methods} FULLY IMPLEMENTABLE methods from this paper.

For each CONCEPT, provide:
- name: Concept name (2-5 words)
- description: Detailed explanation (3-5 sentences) - reference specific sections/figures
- domain: Scientific domain
- relevance: Relevance score 0-1

For each METHOD, provide COMPREHENSIVE implementation details:
- name: Method name (2-5 words) 
- description: DETAILED explanation (10+ sentences) that covers:
  * The exact algorithm from the paper (reference equations by number, e.g., "Eq. 3")
  * Include any figures or tables that illustrate the method
  * Mathematical formulation (transcribe the equations if important)
  * What problem it solves and WHY it works
  * Key hyperparameters from the paper (exact values!)
  * Training procedure and tips from experiments section
  * Performance numbers from the paper's results
- category: One of [loss_function, architecture, training_strategy, feature_engineering, data_augmentation, ensemble, preprocessing, postprocessing, regularization, optimization]
- confidence: Confidence score 0-1
- implementation_hints: SPECIFIC implementation details (5-8 bullet points) including:
  * Exact hyperparameter values from the paper
  * Details from figures/diagrams you can see
  * Training loop details from experiments
  * Common pitfalls mentioned in the paper
- code_snippet: A COMPLETE Python implementation (20-50 lines) that follows the paper exactly. Use PyTorch. Include:
  * Class definition with __init__ and forward
  * All hyperparameters as configurable arguments
  * Comments referencing specific equations/sections
  * Example usage at the end

Return ONLY a JSON object:
```json
{{
  "concepts": [
    {{
      "name": "...",
      "description": "...",
      "domain": "...",
      "relevance": 0.95
    }}
  ],
  "methods": [
    {{
      "name": "...",
      "description": "...",
      "category": "...",
      "confidence": 0.95,
      "implementation_hints": ["...", "..."],
      "code_snippet": "import torch\\n..."
    }}
  ]
}}
```

**CRITICAL REQUIREMENTS:**
1. Reference specific sections, figures, and equations from the PDF you're viewing
2. Extract ACTUAL techniques from this paper, not generic knowledge
3. Include EXACT hyperparameters mentioned in the paper
4. Code must be syntactically correct and runnable
5. Focus on techniques relevant to: protein function prediction, multi-label classification, deep learning"""

    def _extract_relationships(
        self,
        paper: PaperMetadata,
        concepts: List[ExtractedConcept]
    ) -> List[ConceptRelationship]:
        """
        Extract relationships between concepts.

        Args:
            paper: Paper metadata
            concepts: List of extracted concepts

        Returns:
            List of concept relationships
        """
        if len(concepts) < 2:
            return []

        prompt = self._build_relationship_prompt(paper, concepts)

        response_text = self._call_llm(
            prompt,
            system_msg="You are a scientific literature analyst specializing in identifying relationships between concepts."
        )

        if not response_text:
            return []

        parsed = self._parse_json_response(response_text)

        relationships = [
            ConceptRelationship(
                concept1=r.get("concept1", ""),
                concept2=r.get("concept2", ""),
                relationship_type=r.get("type", "RELATED_TO"),
                strength=r.get("strength", 0.5)
            )
            for r in parsed.get("relationships", [])
            if r.get("concept1") and r.get("concept2")
        ]

        return relationships

    def _build_concept_extraction_prompt(
        self,
        paper: PaperMetadata,
        max_concepts: int,
        max_methods: int
    ) -> str:
        """Build prompt for DETAILED concept and method extraction from FULL PDF."""
        # Get full paper text (from PDF if available)
        full_text = self._get_full_paper_text(paper, max_chars=20000)
        
        text = f"Title: {paper.title}\n\n"
        
        if len(full_text) > 1000:
            text += f"FULL PAPER TEXT:\n{full_text}"
        elif paper.abstract:
            text += f"Abstract: {paper.abstract}"
        else:
            text += "Abstract: Not available"

        return f"""You are a senior ML research engineer specializing in implementing techniques from scientific papers.

{text}

Your task: Extract {max_concepts} key concepts and {max_methods} FULLY IMPLEMENTABLE methods from this paper.

**CRITICAL: You are reading the FULL PAPER TEXT. Extract actual algorithms, equations, and implementation details from the paper - not just high-level concepts.**

For each CONCEPT, provide:
- name: Concept name (2-5 words)
- description: Detailed explanation (3-5 sentences) from the paper's text
- domain: Scientific domain
- relevance: Relevance score 0-1

For each METHOD, provide COMPREHENSIVE implementation details:
- name: Method name (2-5 words) 
- description: DETAILED explanation (10+ sentences) that covers:
  * The exact algorithm as described in the paper
  * Mathematical formulation if provided (in words)
  * What problem it solves and WHY it works
  * Key hyperparameters mentioned in the paper
  * Training procedure and tips
  * Expected performance gains mentioned
- category: One of [loss_function, architecture, training_strategy, feature_engineering, data_augmentation, ensemble, preprocessing, postprocessing, regularization, optimization]
- confidence: Confidence score 0-1
- implementation_hints: SPECIFIC implementation details (5-8 bullet points) including:
  * Exact hyperparameter values from the paper
  * Data preprocessing steps
  * Training loop details
  * Evaluation metrics
  * Common pitfalls to avoid
- code_snippet: A COMPLETE Python implementation (20-50 lines) that follows the paper exactly. Use PyTorch. Include:
  * Class definition with __init__ and forward
  * All hyperparameters as configurable arguments
  * Comments explaining each step
  * Example usage at the end

Return ONLY a JSON object:
```json
{{
  "concepts": [
    {{
      "name": "...",
      "description": "...",
      "domain": "...",
      "relevance": 0.95
    }}
  ],
  "methods": [
    {{
      "name": "Attention-Based CNN-LSTM",
      "description": "From Section 3.2 of the paper: The proposed architecture consists of three main components. First, a 1D CNN with kernel size 3 extracts local sequence motifs from the embedded amino acid sequence. The paper uses 64 filters and ReLU activation. Second, a bidirectional LSTM with 128 hidden units processes the CNN output to capture long-range dependencies in both directions. Third, an attention mechanism computes importance weights for each position using a learnable query vector. The paper reports this achieves 0.85 F-max on the test set, a 5% improvement over baseline. Training uses Adam optimizer with lr=0.001 and batch size 32 for 50 epochs with early stopping on validation loss.",
      "category": "architecture",
      "confidence": 0.95,
      "implementation_hints": [
        "Embedding dim: 64 (amino acid vocabulary size = 21 including unknown)",
        "CNN: kernel_size=3, filters=64, padding=1 to preserve sequence length",
        "LSTM: hidden_dim=128, bidirectional=True, dropout=0.3",
        "Attention: Linear(256, 1) followed by softmax over sequence dimension",
        "Output: Linear(256, num_classes) with sigmoid for multi-label",
        "Training: Adam lr=1e-3, batch=32, epochs=50, early_stop_patience=5",
        "Data: Pad sequences to max_len=1000, use masking for variable lengths",
        "Regularization: Dropout 0.3 after each layer, weight_decay=1e-5"
      ],
      "code_snippet": "import torch\\nimport torch.nn as nn\\nimport torch.nn.functional as F\\n\\nclass AttCNNLSTM(nn.Module):\\n    '''Attention-based CNN-LSTM for protein function prediction (from paper Section 3.2)'''\\n    def __init__(self, vocab_size=21, embed_dim=64, cnn_filters=64, lstm_hidden=128, n_classes=1000, dropout=0.3):\\n        super().__init__()\\n        self.embed = nn.Embedding(vocab_size, embed_dim, padding_idx=0)\\n        self.conv = nn.Conv1d(embed_dim, cnn_filters, kernel_size=3, padding=1)\\n        self.lstm = nn.LSTM(cnn_filters, lstm_hidden, bidirectional=True, batch_first=True, dropout=dropout)\\n        self.attn_query = nn.Linear(lstm_hidden * 2, 1)  # Learnable attention\\n        self.dropout = nn.Dropout(dropout)\\n        self.fc = nn.Linear(lstm_hidden * 2, n_classes)\\n\\n    def forward(self, x, mask=None):\\n        # x: (batch, seq_len) - amino acid indices\\n        x = self.embed(x)  # (batch, seq, embed_dim)\\n        x = x.permute(0, 2, 1)  # (batch, embed_dim, seq) for CNN\\n        x = F.relu(self.conv(x))  # (batch, cnn_filters, seq)\\n        x = x.permute(0, 2, 1)  # (batch, seq, cnn_filters) for LSTM\\n        \\n        h, _ = self.lstm(x)  # (batch, seq, lstm_hidden*2)\\n        \\n        # Attention mechanism (Eq. 5 in paper)\\n        attn_scores = self.attn_query(h).squeeze(-1)  # (batch, seq)\\n        if mask is not None:\\n            attn_scores = attn_scores.masked_fill(~mask, -1e9)\\n        attn_weights = F.softmax(attn_scores, dim=1).unsqueeze(-1)  # (batch, seq, 1)\\n        context = (attn_weights * h).sum(dim=1)  # (batch, lstm_hidden*2)\\n        \\n        context = self.dropout(context)\\n        return torch.sigmoid(self.fc(context))  # (batch, n_classes)\\n\\n# Example usage:\\n# model = AttCNNLSTM(vocab_size=21, n_classes=500)\\n# logits = model(torch.randint(0, 21, (32, 500)))  # batch=32, seq_len=500"
    }}
  ]
}}
```

**REQUIREMENTS:**
1. Extract ACTUAL techniques from the paper, not generic knowledge
2. Include specific hyperparameters mentioned in the paper
3. Code must be syntactically correct and runnable
4. Focus on techniques relevant to: protein function prediction, multi-label classification, class imbalance, hierarchical labels
5. If the paper doesn't provide exact values, state "paper does not specify" and provide reasonable defaults"""

    def _build_relationship_prompt(
        self,
        paper: PaperMetadata,
        concepts: List[ExtractedConcept]
    ) -> str:
        """Build prompt for relationship extraction."""
        concept_list = "\n".join([f"- {c.name}: {c.description}" for c in concepts])

        return f"""Based on the paper "{paper.title}", identify relationships between these concepts:

{concept_list}

For each relationship, specify:
- concept1: First concept name (must match exactly one from the list)
- concept2: Second concept name (must match exactly one from the list)
- type: One of [SUBTOPIC_OF, RELATED_TO, PREREQUISITE_FOR, ENABLES, CONTRASTS_WITH, PART_OF, APPLIES_TO]
- strength: Relationship strength 0-1

Return ONLY a JSON object:
```json
{{
  "relationships": [
    {{"concept1": "...", "concept2": "...", "type": "RELATED_TO", "strength": 0.8}},
    ...
  ]
}}
```

Focus on the most important and clear relationships. Only include relationships that are evident from the paper."""

