"""LLM client factory."""

from functools import lru_cache

from llama_index.llms.anthropic import Anthropic
from llama_index.llms.openai import OpenAI

from utils.settings import get_settings


@lru_cache
def get_llm_OpenAI(model: str):
    """Get OpenAI LLM client.

    Returns:
        OpenAI LLM client instance

    Raises:
        ValueError: If required credentials are missing
    """
    config = get_settings()

    if not config.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is required")

    return OpenAI(
        model=model,
        api_key=config.OPENAI_API_KEY,
        max_output_tokens=30000,
        timeout=1000,
    )


@lru_cache
def get_llm_Anthropic(model: str, thinking: bool = False, thinking_budget: int = 10000):
    """Get Anthropic LLM client.

    Args:
        model: Model name to use
        thinking: Enable extended thinking mode (Claude 3.7 Sonnet+)
        thinking_budget: Token budget for thinking process (default: 10000)

    Returns:
        Anthropic LLM client instance
    """
    config = get_settings()

    # Enable thinking mode with required parameters
    if thinking:
        max_tokens = max(64000, thinking_budget + 1000)
        return Anthropic(
            model=model,
            api_key=config.ANTHROPIC_API_KEY,
            max_tokens=max_tokens,
            timeout=1000,
            temperature=1.0,  # Required for thinking mode
            thinking_dict={"type": "enabled", "budget_tokens": thinking_budget},
        )

    return Anthropic(
        model=model,
        api_key=config.ANTHROPIC_API_KEY,
        max_tokens=30000,
        timeout=1000,
    )


@lru_cache
def get_llm(model: str, thinking: bool = False, thinking_budget: int = 10000):
    """Get LLM client based on model name.

    Automatically routes to the appropriate LLM provider based on model name:
    - Models containing "gpt": OpenAI
    - Models containing "claude", "sonnet", or "haiku": Anthropic
    - Default: OpenAI

    Args:
        model: Model name to use
        thinking: Enable extended thinking mode (Anthropic Claude 3.7 Sonnet+ only)
        thinking_budget: Token budget for thinking process (default: 10000)

    Returns:
        LLM client instance
    """
    model_lower = model.lower()

    # Infer provider from model name
    if any(keyword in model_lower for keyword in ["claude", "sonnet", "haiku"]):
        return get_llm_Anthropic(
            model=model, thinking=thinking, thinking_budget=thinking_budget
        )
    elif "gpt" in model_lower:
        return get_llm_OpenAI(model=model)
    else:
        # Default to OpenAI
        return get_llm_OpenAI(model=model)
