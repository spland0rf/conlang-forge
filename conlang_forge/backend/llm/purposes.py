"""Every reason the system calls a model, with the permission it needs and its default model and caps.

Adding a feature that uses a model means adding a purpose here; nothing else may call a provider.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Purpose:
    name: str
    permission: str              # "resource.action": checked with require(); the :own scope is the owner of the conlang
    model: str
    max_output_tokens: int
    temperature: float = 0.0
    description: str = ""


HAIKU, SONNET = "claude-haiku-4-5-20251001", "claude-sonnet-5-5"

PURPOSES = {p.name: p for p in [
    Purpose("exemplar.analyze", "conlang.analyze", SONNET, 3000, 0.0, "read an exemplar text and propose language settings"),
    Purpose("book.polish", "conlang.polish", SONNET, 3000, 0.4, "improve the prose of the generated grammar book"),
    Purpose("translate.reduce", "conlang.translate", HAIKU, 2000, 0.0, "rewrite English into the restricted vocabulary"),
    Purpose("translate.smooth", "conlang.translate", HAIKU, 2000, 0.3, "turn glossed English into natural English"),
    Purpose("admin.test", "llm.test", HAIKU, 500, 0.0, "administrator test call"),
]}
