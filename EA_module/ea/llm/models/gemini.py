import backoff
import openai
import re
from .pricing import GEMINI_MODELS
from .result import QueryResult
import logging
from google import genai  # For Vertex AI Gemini
from google.genai import types

logger = logging.getLogger(__name__)


def backoff_handler(details):
    exc = details.get("exception")
    if exc:
        logger.info(
            f"Gemini - Retry {details['tries']} due to error: {exc}. Waiting {details['wait']:0.1f}s..."
        )


@backoff.on_exception(
    backoff.expo,
    (
        openai.APIConnectionError,
        openai.APIStatusError,
        openai.RateLimitError,
        openai.APITimeoutError,
        Exception,  # For Vertex AI errors
    ),
    max_tries=20,
    max_value=20,
    on_backoff=backoff_handler,
)
def query_gemini(
    client,
    model,
    msg,
    system_msg,
    msg_history,
    output_model,
    model_posteriors=None,
    **kwargs,
) -> QueryResult:
    """Query Gemini model - supports both OpenAI-compatible (LiteLLM) and Vertex AI clients."""
    new_msg_history = msg_history + [{"role": "user", "content": msg}]
    
    # Check if this is a Vertex AI Gemini client or OpenAI-compatible client
    is_vertex_ai = isinstance(client, genai.Client)
    
    if output_model is not None and is_vertex_ai:
        raise ValueError("Vertex AI Gemini does not support structured output yet.")
    
    if is_vertex_ai:
        # ========================================================================
        # VERTEX AI GEMINI (GCP Project-based access)
        # ========================================================================
        # Convert message history to Vertex AI format
        contents = []
        
        # Add system message as first user message (Vertex AI doesn't have system role)
        if system_msg:
            contents.append(f"System: {system_msg}\n\n")
        
        # Add message history
        for hist_msg in msg_history:
            role = "user" if hist_msg["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": hist_msg["content"]}]})
        
        # Add current message
        if contents and isinstance(contents[-1], str):
            # Merge system message with first user message
            contents = contents[:-1] + [contents[-1] + msg]
        else:
            contents.append(msg)
        
        # Call Vertex AI Gemini
        # Build config - only add parameters if they're provided
        config_params = {}
        if "temperature" in kwargs:
            config_params["temperature"] = kwargs["temperature"]
        # Don't set max_output_tokens - let model use its default limit
        
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(**config_params) if config_params else None,
        )
        
        # Extract text from Vertex AI response
        text = str(response.text) if hasattr(response, 'text') else str(response)
        new_msg_history.append({"role": "assistant", "content": text})
        
        # Extract usage info (Vertex AI provides token counts)
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            input_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0) or 0
            output_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0) or 0
        else:
            # Fallback: estimate tokens
            input_tokens = len(str(contents).split())
            output_tokens = len(text.split())
        total_tokens = input_tokens + output_tokens
        
    else:
        # ========================================================================
        # OPENAI-COMPATIBLE CLIENT (LiteLLM or consumer Gemini API)
        # ========================================================================
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_msg},
                *new_msg_history,
            ],
            **kwargs,
        )
        try:
            text = response.choices[0].message.content
        except Exception:
            # Reasoning models - ResponseOutputMessage
            text = response.output[1].content[0].text
        new_msg_history.append({"role": "assistant", "content": text})
        
        input_tokens = response.usage.prompt_tokens
        total_tokens = response.usage.total_tokens
        output_tokens = total_tokens - input_tokens

    # Extract thought tags if present
    thought_match = re.search(
        r"<thought>(.*?)</thought>", text, re.DOTALL
    )
    thought = thought_match.group(1) if thought_match else ""

    content_match = re.search(
        r"<thought>(.*?)</thought>", text, re.DOTALL
    )
    if content_match:
        # Extract everything before and after the <thought> tag as content
        content = (
            text[: content_match.start()]
            + text[content_match.end() :]
        ).strip()
    else:
        content = text

    # Calculate costs
    input_cost = GEMINI_MODELS[model]["input_price"] * input_tokens
    output_cost = GEMINI_MODELS[model]["output_price"] * output_tokens
    
    result = QueryResult(
        content=content,
        msg=msg,
        system_msg=system_msg,
        new_msg_history=new_msg_history,
        model_name=model,
        kwargs=kwargs,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost=input_cost + output_cost,
        input_cost=input_cost,
        output_cost=output_cost,
        thought=thought,
        model_posteriors=model_posteriors,
    )
    return result
