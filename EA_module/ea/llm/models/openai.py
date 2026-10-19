import backoff
import openai
import os
from .pricing import OPENAI_MODELS
from .result import QueryResult
import logging

logger = logging.getLogger(__name__)


def backoff_handler(details):
    exc = details.get("exception")
    if exc:
        logger.warning(
            f"OpenAI - Retry {details['tries']} due to error: {exc}. Waiting {details['wait']:0.1f}s..."
        )


def _is_litellm_client(client) -> bool:
    """Check if client is using LiteLLM proxy (not native OpenAI API)."""
    base_url = str(client.base_url) if hasattr(client, 'base_url') else ""
    return "litellm" in base_url.lower() or (
        os.getenv("OPENAI_API_BASE") and "litellm" in os.getenv("OPENAI_API_BASE", "").lower()
    )


@backoff.on_exception(
    backoff.expo,
    (
        openai.APIConnectionError,
        openai.APIStatusError,
        openai.RateLimitError,
        openai.APITimeoutError,
    ),
    max_tries=20,
    max_value=20,
    on_backoff=backoff_handler,
)
def query_openai(
    client,
    model,
    msg,
    system_msg,
    msg_history,
    output_model,
    model_posteriors=None,
    **kwargs,
) -> QueryResult:
    """Query OpenAI model.
    
    Uses chat.completions API for LiteLLM proxy, responses API for native OpenAI.
    """
    new_msg_history = msg_history + [{"role": "user", "content": msg}]
    
    # Use chat.completions for LiteLLM proxy (responses API not supported)
    use_chat_completions = _is_litellm_client(client)
    
    if use_chat_completions:
        # LiteLLM proxy - use chat.completions API
        messages = [
            {"role": "system", "content": system_msg},
            *new_msg_history,
        ]
        
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            **kwargs,
        )
        content = response.choices[0].message.content
        new_msg_history.append({"role": "assistant", "content": content})
        
        input_tokens = response.usage.prompt_tokens if response.usage else 0
        output_tokens = response.usage.completion_tokens if response.usage else 0
        
    else:
        # Native OpenAI - use responses API
        if output_model is None:
            response = client.responses.create(
                model=model,
                input=[
                    {"role": "system", "content": system_msg},
                    *new_msg_history,
                ],
                **kwargs,
            )
            try:
                content = response.output[0].content[0].text
            except Exception:
                # Reasoning models - ResponseOutputMessage
                content = response.output[1].content[0].text
            new_msg_history.append({"role": "assistant", "content": content})
        else:
            response = client.responses.parse(
                model=model,
                input=[
                    {"role": "system", "content": system_msg},
                    *new_msg_history,
                ],
                text_format=output_model,
                **kwargs,
            )
            content = response.output_parsed
            new_content = ""
            for i in content:
                new_content += i[0] + ":" + i[1] + "\n"
            new_msg_history.append({"role": "assistant", "content": new_content})
        
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
    
    # Calculate costs (use default pricing if model not in list)
    pricing = OPENAI_MODELS.get(model, {"input_price": 0.01, "output_price": 0.03})
    input_cost = pricing["input_price"] * input_tokens
    output_cost = pricing["output_price"] * output_tokens
    
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
        thought="",
        model_posteriors=model_posteriors,
    )
    return result
