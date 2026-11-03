from __future__ import annotations

import httpx

from ..config import Settings
from .base import Image, LLMError


class MockProvider:
    """API Key 없이 데모를 돌리기 위한 자리표시자. 실제 생성은 mock 로직(evaluation/companion)이 담당."""
    name = "mock"
    is_mock = True
    supports_vision = False

    def complete(self, system, messages, images=None, max_tokens=700) -> str:  # pragma: no cover - 호출되지 않음
        raise LLMError("mock provider does not generate text")


class AnthropicProvider:
    name = "anthropic"
    is_mock = False
    supports_vision = True

    def __init__(self, api_key: str, model: str):
        if not api_key:
            raise LLMError("ANTHROPIC_API_KEY 가 설정되지 않았습니다.")
        self.api_key, self.model = api_key, model

    def complete(self, system, messages, images: list[Image] | None = None, max_tokens=700) -> str:
        msgs = [dict(m) for m in messages]
        if images and msgs and msgs[-1]["role"] == "user":
            blocks = [{"type": "image", "source": {"type": "base64", "media_type": mt, "data": data}} for mt, data in images]
            blocks.append({"type": "text", "text": msgs[-1]["content"]})
            msgs[-1] = {"role": "user", "content": blocks}
        try:
            r = httpx.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": self.api_key, "anthropic-version": "2023-06-01"},
                json={"model": self.model, "max_tokens": max_tokens, "system": system, "messages": msgs},
                timeout=60,
            )
            r.raise_for_status()
            return "".join(b.get("text", "") for b in r.json()["content"] if b.get("type") == "text")
        except (httpx.HTTPError, KeyError, ValueError) as e:
            raise LLMError(f"Anthropic 호출 실패: {type(e).__name__}") from e


class OpenAICompatibleProvider:
    """OpenAI Chat Completions 호환 엔드포인트 (OpenAI, 로컬 서버 등)."""
    name = "openai_compatible"
    is_mock = False

    def __init__(self, api_key: str, base_url: str, model: str):
        if not model:
            raise LLMError("OPENAI_MODEL 이 설정되지 않았습니다.")
        self.api_key, self.base_url, self.model = api_key, base_url.rstrip("/"), model
        self.supports_vision = True  # 모델이 비전을 지원하지 않으면 제공자가 오류를 반환한다.

    def complete(self, system, messages, images: list[Image] | None = None, max_tokens=700) -> str:
        msgs = [{"role": "system", "content": system}, *[dict(m) for m in messages]]
        if images and msgs[-1]["role"] == "user":
            parts = [{"type": "text", "text": msgs[-1]["content"]}]
            parts += [{"type": "image_url", "image_url": {"url": f"data:{mt};base64,{d}"}} for mt, d in images]
            msgs[-1] = {"role": "user", "content": parts}
        try:
            r = httpx.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.model, "messages": msgs, "max_tokens": max_tokens},
                timeout=60,
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as e:
            raise LLMError(f"OpenAI 호환 호출 실패: {type(e).__name__}") from e


def get_provider(s: Settings):
    if s.llm_provider == "anthropic":
        return AnthropicProvider(s.anthropic_api_key, s.anthropic_model)
    if s.llm_provider == "openai_compatible":
        return OpenAICompatibleProvider(s.openai_api_key, s.openai_base_url, s.openai_model)
    return MockProvider()
