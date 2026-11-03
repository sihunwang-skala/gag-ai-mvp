"""Provider-agnostic LLM Adapter.

모든 제공자는 `complete(system, messages, images)` 하나만 구현한다.
messages: [{"role": "user"|"assistant", "content": str}]
images: [(mime_type, base64_str)] — 비전 지원 제공자만 사용.
"""
from __future__ import annotations

from typing import Protocol

Image = tuple[str, str]


class LLMError(RuntimeError):
    pass


class LLMProvider(Protocol):
    name: str
    is_mock: bool
    supports_vision: bool

    def complete(self, system: str, messages: list[dict], images: list[Image] | None = None, max_tokens: int = 700) -> str: ...
