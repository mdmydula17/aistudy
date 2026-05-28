from langchain_openai import ChatOpenAI

from app.core.config import (
    get_deepseek_api_key,
    get_deepseek_base_url,
    get_deepseek_model,
)


def get_chat_llm(temperature: float = 0.1) -> ChatOpenAI:
    return ChatOpenAI(
        api_key=get_deepseek_api_key(),
        base_url=f"{get_deepseek_base_url()}/v1",
        model=get_deepseek_model(),
        temperature=temperature,
    )


def get_vision_llm(temperature: float = 0.0) -> ChatOpenAI:
    return ChatOpenAI(
        api_key=get_deepseek_api_key(),
        base_url=f"{get_deepseek_base_url()}/v1",
        model=get_deepseek_model(),
        temperature=temperature,
    )
