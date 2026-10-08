from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Message:
    role: str          # "user" or "assistant"
    content: str


@dataclass(frozen=True)
class LLMRequest:
    model: str
    messages: tuple
    system: str = ""
    max_tokens: int = 1024
    temperature: float = 0.0
    cache_system: bool = False        # ask the provider to cache the (long, repeated) system prompt

    @property
    def chars(self) -> int:
        return len(self.system) + sum(len(m.content) for m in self.messages)


@dataclass(frozen=True)
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_write_tokens: int = 0
    cache_read_tokens: int = 0

    @property
    def quota_tokens(self) -> int:
        """What counts against a user's allowance: everything processed, with cheap cache reads at one tenth."""
        return self.input_tokens + self.output_tokens + self.cache_write_tokens + self.cache_read_tokens // 10


@dataclass(frozen=True)
class LLMResponse:
    text: str
    usage: Usage
    model: str
    stop_reason: str = ""
    provider_request_id: str = ""
    extra: dict = field(default_factory=dict)
