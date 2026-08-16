"""
Universal LLM Worker for Scientific Code Generation
=================================================

Supports both Gemini 2.5 Pro and OpenAI models for generating and improving
domain-specific scientific code. Automatically detects available providers
and provides fallback options.
"""

import os
import traceback
from typing import Optional, Dict, Any, List
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """Response from LLM code generation."""
    code: Optional[str]
    success: bool
    error_message: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None


class UniversalLLMWorker:
    """Universal LLM worker supporting multiple providers."""
    
    def __init__(self, preferred_provider: str = "gemini", model_name: Optional[str] = None):
        """
        Initialize LLM worker with preferred provider.
        
        Args:
            preferred_provider: "gemini" or "openai"
            model_name: Specific model name (optional)
        """
        self.preferred_provider = preferred_provider.lower()
        self.model_name = model_name
        self.gemini_client = None
        self.openai_client = None
        
        # Initialize available providers
        self._setup_providers()
        
        # Select active provider
        self.active_provider = self._select_provider()
        
    def _setup_providers(self):
        """Setup available LLM providers."""
        # Setup Gemini 2.5 Pro
        try:
            google_project = os.environ.get("GOOGLE_CLOUD_PROJECT")
            if google_project:
                from google import genai
                from google.genai import types
                
                self.gemini_client = genai.Client(
                    vertexai=True,
                    project=google_project,
                    location="us-central1"
                )
                print(f"✅ Gemini 2.5 Pro initialized with project: {google_project}")
        except Exception as e:
            print(f"⚠️ Gemini setup failed: {e}")
            self.gemini_client = None
        
        # Setup OpenAI
        try:
            openai_key = os.environ.get("OPENAI_API_KEY")
            if openai_key:
                from openai import OpenAI
                self.openai_client = OpenAI(api_key=openai_key)
                print(f"✅ OpenAI initialized")
        except Exception as e:
            print(f"⚠️ OpenAI setup failed: {e}")
            self.openai_client = None
    
    def _select_provider(self) -> str:
        """Select the active provider based on availability and preference."""
        if self.preferred_provider == "gemini" and self.gemini_client:
            return "gemini"
        elif self.preferred_provider == "openai" and self.openai_client:
            return "openai"
        elif self.gemini_client:  # Fallback to Gemini
            return "gemini"
        elif self.openai_client:  # Fallback to OpenAI
            return "openai"
        else:
            raise RuntimeError("No LLM provider available. Please set up either GOOGLE_CLOUD_PROJECT or OPENAI_API_KEY")
    
    def generate_code_mutation(
        self, 
        previous_code: str, 
        score: float, 
        task_description: str,
        research_ideas: Optional[List[str]] = None,
        domain: str = "machine_learning",
        data_files: Optional[Dict[str, str]] = None
    ) -> LLMResponse:
        """
        Generate improved code based on previous version and performance.
        
        Args:
            previous_code: The previous code version
            score: Performance score of previous code
            task_description: Description of the scientific task
            research_ideas: Optional list of research ideas to incorporate
            domain: Scientific domain for context
            data_files: Optional dictionary of data file paths
            
        Returns:
            LLMResponse with generated code or error information
        """
        if self.active_provider == "gemini":
            return self._generate_with_gemini(previous_code, score, task_description, research_ideas, domain, data_files)
        elif self.active_provider == "openai":
            return self._generate_with_openai(previous_code, score, task_description, research_ideas, domain, data_files)
        else:
            return LLMResponse(
                code=None,
                success=False,
                error_message="No LLM provider available"
            )
    
    def generate_initial_code(
        self, 
        task_description: str,
        domain: str = "machine_learning",
        research_ideas: Optional[List[str]] = None,
        data_files: Optional[Dict[str, str]] = None,
        embedding_model: Optional[str] = None
    ) -> LLMResponse:
        """
        Generate initial code for a scientific task.
        
        Args:
            task_description: Description of the scientific task
            domain: Scientific domain for context
            research_ideas: Optional list of research ideas to incorporate
            data_files: Optional dictionary of data file paths
            embedding_model: Optional specific embedding model to use
            
        Returns:
            LLMResponse with generated code or error information
        """
        if self.active_provider == "gemini":
            return self._generate_initial_with_gemini(task_description, domain, research_ideas, data_files, embedding_model)
        elif self.active_provider == "openai":
            return self._generate_initial_with_openai(task_description, domain, research_ideas, data_files, embedding_model)
        else:
            return LLMResponse(
                code=None,
                success=False,
                error_message="No LLM provider available"
            )
    
    def _generate_with_gemini(
        self, 
        previous_code: str, 
        score: float, 
        task_description: str,
        research_ideas: Optional[List[str]] = None,
        domain: str = "machine_learning",
        data_files: Optional[Dict[str, str]] = None
    ) -> LLMResponse:
        """Generate improved code using Gemini 2.5 Pro."""
        try:
            from google.genai import types
            
            system_prompt = self._create_system_prompt(domain)
            user_prompt = self._create_mutation_prompt(previous_code, score, task_description, research_ideas, data_files)
            
            model_name = self.model_name or "gemini-2.5-pro"
            
            response = self.gemini_client.models.generate_content(
                model=model_name,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.7
                    # No max_output_tokens limit - let Gemini generate complete code
                ),
                contents=user_prompt
            )
            
            code = self._extract_code_from_response(response.text)
            
            return LLMResponse(
                code=code,
                success=True,
                provider="gemini",
                model=model_name
            )
            
        except Exception as e:
            return LLMResponse(
                code=None,
                success=False,
                error_message=f"Gemini API error: {str(e)}",
                provider="gemini"
            )
    
    def _generate_with_openai(
        self, 
        previous_code: str, 
        score: float, 
        task_description: str,
        research_ideas: Optional[List[str]] = None,
        domain: str = "machine_learning",
        data_files: Optional[Dict[str, str]] = None
    ) -> LLMResponse:
        """Generate improved code using OpenAI."""
        try:
            system_prompt = self._create_system_prompt(domain)
            user_prompt = self._create_mutation_prompt(previous_code, score, task_description, research_ideas, data_files)
            
            model_name = self.model_name or "gpt-4-turbo-preview"
            
            response = self.openai_client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=4000
            )
            
            code = self._extract_code_from_response(response.choices[0].message.content)
            
            return LLMResponse(
                code=code,
                success=True,
                provider="openai",
                model=model_name
            )
            
        except Exception as e:
            return LLMResponse(
                code=None,
                success=False,
                error_message=f"OpenAI API error: {str(e)}",
                provider="openai"
            )
    
    def _generate_initial_with_gemini(
        self,
        task_description: str,
        domain: str = "machine_learning",
        research_ideas: Optional[List[str]] = None,
        data_files: Optional[Dict[str, str]] = None,
        embedding_model: Optional[str] = None
    ) -> LLMResponse:
        """Generate initial code using Gemini 2.5 Pro."""
        try:
            from google.genai import types
            
            system_prompt = self._create_system_prompt(domain)
            user_prompt = self._create_initial_prompt(task_description, research_ideas, data_files, embedding_model)
            
            model_name = self.model_name or "gemini-2.5-pro"
            print("---------------initial code prompt-----------------")
            print(f"🔍 Gemini 2.5 Pro model name: {model_name}")
            print(f"🔍 Gemini 2.5 Pro system prompt: {system_prompt}")
            print(f"🔍 Gemini 2.5 Pro user prompt: {user_prompt}")
            
            response = self.gemini_client.models.generate_content(
                model=model_name,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.5  # Lower temperature for initial code
                    # No max_output_tokens limit - let Gemini generate complete code
                ),
                contents=user_prompt
            )
    
            
            code = self._extract_code_from_response(response.text)
            
            return LLMResponse(
                code=code,
                success=True,
                provider="gemini",
                model=model_name
            )
            
        except Exception as e:
            return LLMResponse(
                code=None,
                success=False,
                error_message=f"Gemini API error: {str(e)}",
                provider="gemini"
            )
    
    def _generate_initial_with_openai(
        self,
        task_description: str,
        domain: str = "machine_learning",
        research_ideas: Optional[List[str]] = None,
        data_files: Optional[Dict[str, str]] = None,
        embedding_model: Optional[str] = None
    ) -> LLMResponse:
        """Generate initial code using OpenAI."""
        try:
            system_prompt = self._create_system_prompt(domain)
            user_prompt = self._create_initial_prompt(task_description, research_ideas, data_files, embedding_model)
            
            model_name = self.model_name or "gpt-4-turbo-preview"
            
            response = self.openai_client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.5,  # Lower temperature for initial code
                max_tokens=4000
            )
            
            code = self._extract_code_from_response(response.choices[0].message.content)
            
            return LLMResponse(
                code=code,
                success=True,
                provider="openai",
                model=model_name
            )
            
        except Exception as e:
            return LLMResponse(
                code=None,
                success=False,
                error_message=f"OpenAI API error: {str(e)}",
                provider="openai"
            )
    
    def _create_system_prompt(self, domain: str) -> str:
        """Create domain-appropriate system prompt."""
        domain_contexts = {
            "machine_learning": "You are an expert machine learning engineer specializing in automated model discovery and optimization.",
            "bioinformatics": "You are an expert bioinformatics researcher specializing in computational biology and genomics analysis.",
            "epidemiology": "You are an expert epidemiologist specializing in disease modeling and public health analytics.",
            "geospatial": "You are an expert in geospatial analysis and remote sensing with deep knowledge of GIS and satellite imagery.",
            "time_series": "You are an expert in time series analysis and forecasting with deep knowledge of temporal modeling.",
            "neuroscience": "You are an expert neuroscientist specializing in computational neuroscience and neural data analysis.",
            "climate": "You are an expert climate scientist specializing in climate modeling and meteorological analysis.",
        }
        
        base_context = domain_contexts.get(domain, "You are an expert scientific programmer specializing in data analysis and computational research.")
        
        return f"""{base_context}

Your task is to write high-quality Python code that achieves the best possible performance on scientific tasks.
You have extensive knowledge of:
- Advanced algorithms and statistical methods
- State-of-the-art machine learning techniques
- Domain-specific best practices
- Performance optimization strategies
- Error handling and robust code design

Always provide complete, runnable code that is well-documented and follows best practices."""
    
    def _create_mutation_prompt(
        self, 
        previous_code: str, 
        score: float, 
        task_description: str,
        research_ideas: Optional[List[str]] = None,
        data_files: Optional[Dict[str, str]] = None
    ) -> str:
        """Create prompt for code mutation/improvement."""
        prompt = f"""
Your task is to improve a piece of Python code for a scientific task.

**Task Description:**
{task_description}

"""
        
        if data_files:
            prompt += """
**Data Files (use these exact absolute paths):**
"""
            for key, path in data_files.items():
                prompt += f"- {key}: {path}\n"
            prompt += "\n"

        prompt += f"""
**Previous Code:**
```python
{previous_code}
```

**Performance of Previous Code:**
The code above achieved a score of: {score:.4f}. A higher score is better.

**Your Goal:**
Rewrite the code to achieve a higher score. You can try different approaches such as:
- Different models or algorithms
- Advanced feature engineering
- Hyperparameter optimization
- Ensemble methods
- Data preprocessing improvements
- Handling of edge cases

"""
        
        if research_ideas:
            prompt += f"""
**Research Ideas to Consider:**
{chr(10).join(f'- {idea}' for idea in research_ideas)}

"""
        
        prompt += """
**Requirements:**
- The code MUST be a complete, runnable script
- Use the exact file paths provided above for data loading
- It must define the required output variable containing the predictions
- Include all necessary imports and error handling
- Follow best practices for the scientific domain
- Optimize for the specified evaluation metric

Provide only the complete, raw Python code inside a single code block. Do not add any explanation.
"""
        
        return prompt
    
    def _create_initial_prompt(
        self,
        task_description: str,
        research_ideas: Optional[List[str]] = None,
        data_files: Optional[Dict[str, str]] = None,
        embedding_model: Optional[str] = None
    ) -> str:
        """Create prompt for initial code generation."""
        prompt = f"""
Write Python code to solve the following scientific task:

**Task Description:**
{task_description}

"""
        
        if data_files:
            prompt += """
**Data Files (use these exact absolute paths):**
"""
            for key, path in data_files.items():
                prompt += f"- {key}: {path}\n"
            prompt += "\n"
        
        # Add explicit embedding model requirement if specified
        if embedding_model:
            prompt += f"""
**⚠️ CRITICAL REQUIREMENT - EMBEDDING MODEL:**
YOU MUST USE THIS EXACT MODEL: {embedding_model}
DO NOT substitute with any other embedding model!
Use either sentence-transformers or transformers library to load this model.

**⚠️ CRITICAL MEMORY SETTINGS - PRECISION & BATCH SIZE:**
For large embedding models like Qwen3-Embedding-8B (8B parameters):
1. **Load in bfloat16 precision** (reduces 37GB → 18GB VRAM)
2. **USE batch_size=4** (recommended)  
3. **MAXIMUM batch_size=8** (DO NOT exceed!)

Without these settings, you WILL get CUDA Out of Memory errors!

Example usage:
```python
import torch
from sentence_transformers import SentenceTransformer

# CRITICAL: Load model in bfloat16 to save VRAM!
model = SentenceTransformer(
    "{embedding_model}",
    trust_remote_code=True,
    device='cuda',
    model_kwargs={{'torch_dtype': torch.bfloat16}}  # MANDATORY for 40GB GPU!
)

# CRITICAL: Use small batch size for large embedding models!
train_embeddings = model.encode(
    train_texts, 
    batch_size=4,  # MANDATORY for large models!
    show_progress_bar=True
)

# OR with transformers
from transformers import AutoModel, AutoTokenizer
model = AutoModel.from_pretrained("{embedding_model}")
tokenizer = AutoTokenizer.from_pretrained("{embedding_model}")

# Process in small batches (4-8 samples max)
for i in range(0, len(texts), 4):  # batch_size=4
    batch = texts[i:i+4]
    # ... process batch ...
```

"""
        
        if research_ideas:
            prompt += f"""
**Research Ideas to Consider:**
{chr(10).join(f'- {idea}' for idea in research_ideas)}

"""
        
        prompt += """
**Requirements:**
- Write complete, runnable Python code
- Use the exact file paths provided above for data loading
- Include all necessary imports
- Handle data loading and preprocessing
- Implement appropriate models/algorithms
- Generate the required predictions
- Follow scientific programming best practices
- Include basic error handling

**⚠️ CRITICAL - REQUIRED OUTPUT:**
1. You MUST define the output variable as specified in the task description (e.g., `test_predictions`)
2. **CRITICAL:** You MUST calculate and store the final score in a variable named `score`
   - This is MANDATORY - the system will fail without it!
   - After calculating your metric, assign it to `score` variable
   - Example: `score = f1_score(...)` or `score = calculated_f1_value`
3. **IMPORTANT**: Calculate the score on the TEST SET (test.csv has labels), not just validation set
4. **F1 SCORE**: When calculating f1_score, use `average='micro'` (micro-averaged F1 score)
5. The system will AUTOMATICALLY save results to JSON - DO NOT include your own JSON saving code
6. DO NOT write `json.dump()` or save to files - result collection is automatic

**⚠️ SCORE VARIABLE IS MANDATORY! Example patterns:**
```python
# Pattern 1: Direct assignment
score = f1_score(y_true, y_pred, average='micro')

# Pattern 2: Calculate then assign
f1_result = f1_score(y_true, y_pred, average='micro')
score = f1_result  # ← REQUIRED! Must assign to 'score'

# Pattern 3: With printing
calculated_f1 = f1_score(y_true, y_pred, average='micro')
print(f"F1 Score: {{calculated_f1:.4f}}")
score = calculated_f1  # ← REQUIRED! Must assign to 'score'
```

Full example structure:
```python
import pandas as pd
from sklearn.metrics import f1_score

# Load data
train_df = pd.read_csv('/absolute/path/to/train.csv')
test_df = pd.read_csv('/absolute/path/to/test.csv')  # test.csv HAS labels!

# ... your model training code ...

# Make predictions on test set
test_predictions = model.predict(test_df)  # As specified in task

# REQUIRED: Calculate score on TEST SET (not just validation!)
# Extract true labels from test_df and compare with test_predictions
calculated_f1 = f1_score(test_true_labels, test_predictions, average='micro')

# ⚠️ CRITICAL: Assign to 'score' variable - MANDATORY!
score = calculated_f1

print(f"Final score: {{score:.4f}}")  # Optional: print for logging
```

Provide only the complete, raw Python code inside a single code block. Do not add any explanation.
"""
        
        return prompt
    
    def _extract_code_from_response(self, response_text: str) -> Optional[str]:
        """Extract Python code from LLM response."""
        if not response_text:
            return None
        
        # Try to extract code block
        if '```python' in response_text:
            try:
                code = response_text.split('```python')[1].split('```')[0].strip()
                return code
            except IndexError:
                pass
        
        # Try generic code block
        if '```' in response_text:
            try:
                code = response_text.split('```')[1].split('```')[0].strip()
                # Remove language identifier if present
                lines = code.split('\n')
                if lines and lines[0].strip() in ['python', 'py']:
                    code = '\n'.join(lines[1:])
                return code
            except IndexError:
                pass
        
        # Return the entire response if no code blocks found
        return response_text.strip()


# Global instance for backward compatibility
_global_worker = None

def get_llm_worker(preferred_provider: str = "gemini") -> UniversalLLMWorker:
    """Get or create global LLM worker instance."""
    global _global_worker
    if _global_worker is None:
        _global_worker = UniversalLLMWorker(preferred_provider=preferred_provider)
    return _global_worker

def generate_code_mutation(
    previous_code: str, 
    score: float, 
    task_description: str,
    research_ideas: Optional[List[str]] = None,
    domain: str = "machine_learning"
) -> Optional[str]:
    """
    Legacy function for backward compatibility.
    Generate improved code based on previous version and performance.
    
    Returns:
        Generated code string or None if failed
    """
    worker = get_llm_worker()
    response = worker.generate_code_mutation(previous_code, score, task_description, research_ideas, domain)
    return response.code if response.success else None

def generate_initial_code(
    task_description: str,
    domain: str = "machine_learning",
    research_ideas: Optional[List[str]] = None
) -> Optional[str]:
    """
    Legacy function for backward compatibility.
    Generate initial code for a scientific task.
    
    Returns:
        Generated code string or None if failed
    """
    worker = get_llm_worker()
    response = worker.generate_initial_code(task_description, domain, research_ideas)
    return response.code if response.success else None