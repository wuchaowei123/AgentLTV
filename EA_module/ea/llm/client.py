from typing import Any, Tuple
import os
import anthropic
import openai
import instructor
from pathlib import Path
from dotenv import load_dotenv
from google import genai  # For GCP Vertex AI Gemini access
from .models.pricing import (
    CLAUDE_MODELS,
    BEDROCK_MODELS,
    OPENAI_MODELS,
    DEEPSEEK_MODELS,
    GEMINI_MODELS,
)

env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)


def get_client_llm(model_name: str, structured_output: bool = False) -> Tuple[Any, str]:
    """Get the client and model for the given model name.

    Args:
        model_name (str): The name of the model to get the client.

    Raises:
        ValueError: If the model is not supported.

    Returns:
        The client and model for the given model name.
    """
    # print(f"Getting client for model {model_name}")
    # Check if using LiteLLM proxy for Claude models (e.g., claude-sonnet-4-5)
    litellm_api_base = os.getenv("OPENAI_API_BASE")
    litellm_api_key = os.getenv("OPENAI_API_KEY")
    
    # Route through LiteLLM proxy if model starts with claude- and proxy is configured
    if model_name.startswith("claude-") and litellm_api_base and model_name not in CLAUDE_MODELS.keys():
        # Use OpenAI-compatible endpoint for LiteLLM proxy
        client = openai.OpenAI(
            api_key=litellm_api_key,
            base_url=litellm_api_base,
        )
        if structured_output:
            client = instructor.from_openai(client, mode=instructor.Mode.TOOLS_STRICT)
    elif model_name in CLAUDE_MODELS.keys():
        client = anthropic.Anthropic()
        if structured_output:
            client = instructor.from_anthropic(
                client, mode=instructor.mode.Mode.ANTHROPIC_JSON
            )
    elif model_name in BEDROCK_MODELS.keys():
        model_name = model_name.split("/")[-1]
        client = anthropic.AnthropicBedrock(
            aws_access_key=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            aws_region=os.getenv("AWS_REGION_NAME"),
        )
        if structured_output:
            client = instructor.from_anthropic(
                client, mode=instructor.mode.Mode.ANTHROPIC_JSON
            )
    elif model_name in OPENAI_MODELS.keys() or model_name.startswith("gpt-") or model_name.startswith("o1-") or model_name.startswith("o3-"):
        # Use OPENAI_API_BASE for LiteLLM proxy support
        api_base = os.getenv("OPENAI_API_BASE")
        api_key = os.getenv("OPENAI_API_KEY")
        
        if api_base:
            # Using LiteLLM proxy
            client = openai.OpenAI(
                api_key=api_key,
                base_url=api_base,
            )
        else:
            # Direct OpenAI API
            client = openai.OpenAI()
        
        if structured_output:
            client = instructor.from_openai(client, mode=instructor.Mode.TOOLS_STRICT)
    elif model_name.startswith("azure-"):
        # get rid of the azure- prefix
        model_name = model_name.split("azure-")[-1]
        client = openai.AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_API_VERSION"),
            azure_endpoint=os.getenv("AZURE_API_ENDPOINT"),
        )
        if structured_output:
            client = instructor.from_openai(client, mode=instructor.Mode.TOOLS_STRICT)
    elif model_name in DEEPSEEK_MODELS.keys():
        client = openai.OpenAI(
            api_key=os.environ["DEEPSEEK_API_KEY"],
            base_url="https://api.deepseek.com",
        )
        if structured_output:
            client = instructor.from_openai(client, mode=instructor.Mode.MD_JSON)
    elif model_name in GEMINI_MODELS.keys():
        # Use GCP Vertex AI for Gemini models (project-based access)
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "prefab-root-439302-c5")
        
        # Gemini 3 requires location="global", others can use "us-central1"
        location = "global" if "gemini-3" in model_name or "gemini-exp" in model_name else "us-central1"
        
        client = genai.Client(
            vertexai=True,
            project=project_id,
            location=location,
        )
        
        # Note: structured_output with Vertex AI Gemini uses a different approach
        # For now, we don't wrap with instructor for Vertex AI
        # TODO: Implement structured output for Vertex AI if needed
    else:
        raise ValueError(f"Model {model_name} not supported.")

    return client, model_name
