"""DashScope Qwen-Plus LLM wrapper compatible with neo4j-graphrag."""

from openai import OpenAI
from pydantic import BaseModel

from backend.config import settings


class LLMResponse(BaseModel):
    """Standard LLM response format."""

    content: str


class DashScopeLLM:
    """DashScope LLM wrapper using OpenAI-compatible interface.
    Works with Qwen-Plus and other Qwen models.
    """

    def __init__(
        self,
        model: str = None,
        api_key: str = None,
        base_url: str = None,
        temperature: float = None,
        max_tokens: int = 2048,
        **kwargs
    ):
        self.model = model or settings.llm_model
        self.temperature = temperature if temperature is not None else settings.llm_temperature
        self.max_tokens = max_tokens

        self.client = OpenAI(
            api_key=api_key or settings.dashscope_api_key,
            base_url=base_url or settings.dashscope_base_url,
        )

    def invoke(self, input_text: str, **kwargs) -> LLMResponse:
        """Invoke the LLM with a text prompt.

        Args:
            input_text: The prompt text
            **kwargs: Additional arguments passed to the API

        Returns:
            LLMResponse with the generated content

        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": input_text}],
            temperature=kwargs.get("temperature", self.temperature),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
        )

        content = response.choices[0].message.content or ""
        return LLMResponse(content=content)

    async def ainvoke(self, input_text: str, **kwargs) -> LLMResponse:
        """Async version of invoke (uses sync client internally)."""
        # For now, use sync client. Can be upgraded to AsyncOpenAI later.
        return self.invoke(input_text, **kwargs)

    def chat(
        self,
        messages: list[dict[str, str]],
        **kwargs
    ) -> LLMResponse:
        """Chat with the LLM using a list of messages.

        Args:
            messages: List of {"role": "user"|"assistant"|"system", "content": "..."}
            **kwargs: Additional arguments

        Returns:
            LLMResponse with the generated content

        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=kwargs.get("temperature", self.temperature),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
            stream=kwargs.get("stream", False),
        )

        if kwargs.get("stream", False):
            return response  # Return generator for streaming

        content = response.choices[0].message.content or ""
        return LLMResponse(content=content)

    def stream_chat(
        self,
        messages: list[dict[str, str]],
        **kwargs
    ):
        """Stream chat responses."""
        return self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=kwargs.get("temperature", self.temperature),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
            stream=True,
        )


# Singleton instance
_llm_instance: DashScopeLLM | None = None


def get_llm() -> DashScopeLLM:
    """Get or create the DashScopeLLM instance."""
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = DashScopeLLM()
    return _llm_instance


# LangChain ChatOpenAI singleton for better compatibility
_langchain_llm_instance = None


def get_langchain_llm():
    """Get or create a LangChain ChatOpenAI instance.

    This provides better compatibility with LangChain chains like
    GraphCypherQAChain and uses the same DashScope API.
    """
    global _langchain_llm_instance
    if _langchain_llm_instance is None:
        from langchain_openai import ChatOpenAI
        _langchain_llm_instance = ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.dashscope_api_key,
            base_url=settings.dashscope_base_url,
            temperature=settings.llm_temperature,
        )
    return _langchain_llm_instance
