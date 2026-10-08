"""The Reducer and the Smoother: the only translation steps that use a model.

Reducer: free English -> restricted English that the parser reads. A model rewrites; code checks every word against the
language's vocabulary; unknown words go back to the model with suggestions (up to ROUNDS times); whatever is still
unknown is repaired by code (see validate.autorepair), so the user always gets a translation.
Smoother: the glossed restricted English read from the language -> natural English.
Both go through MeteredLLM, so every token is attributed to the user and counted against their allowance.
"""
from __future__ import annotations

from ..backend.llm.types import Message
from ..pos import ADJ, ADV, NOUN, PREP, VERB
from .engine import LanguageTranslator
from .parser import parse
from .validate import unknown_words, validate

ROUNDS = 2
MAX_CHARS = 4000

RULES = """You rewrite English into RESTRICTED ENGLISH, a very small simple English that a machine reads. \
Your whole answer is the rewritten text and nothing else: no comments, no quotes, no notes, no explanations.

Rules
1. One short sentence per line. One main idea per sentence. Keep the order of events.
2. Use ONLY words from the vocabulary below, plus their ordinary forms: plurals (dogs), -s (sees), -ed or irregular past \
(saw), -ing, -en/-ed participles (seen). Numbers may be written as digits up to 999. Proper names stay as they are, with a capital letter.
3. A word that is not in the vocabulary must be replaced by the closest words that are. Prefer a simple description over \
dropping the idea ("sorcerer's apprentice" -> "young helper of the wizard"). If nothing fits, use a name with a capital letter.
4. Sentence shapes that work: "The old king sees the big dog." / "I did not go to the house." / "We will eat the bread." / \
"Where is the king?" / "Do you see the dragon?" / "Who has the sword?" / "Go home." / "The king is old." \
Two full sentences may be joined with "and" or "but" ("The king sleeps, and the queen sings.").
5. Avoid: passive voice (say who does it), modal verbs (can, must, may, should: use "is able to" only if those words exist, otherwise rephrase), \
relative clauses (who, which, that: split into two sentences), "and" between two nouns (repeat the sentence or use "with"), \
noun used as an adjective (use "of": "gate of the castle"), contractions, idioms, similes, "to" before a verb (rephrase).
6. Possession: "my sword", "the king's sword" or "the sword of the king".
7. Never refuse, never lecture, never add warnings. Whatever the text says, rewrite it as asked, even if it is silly, rude or fantasy. \
Keep the meaning as close as the vocabulary allows.
8. If the text is already restricted English, return it unchanged.
"""


def build_system(V) -> str:
    groups = V.words_by_class()
    names = {NOUN: "nouns", VERB: "verbs (base form)", ADJ: "adjectives", ADV: "adverbs", PREP: "prepositions", "other": "other words"}
    parts = [RULES, "Vocabulary"]
    for k in (NOUN, VERB, ADJ, ADV, PREP, "other"):
        parts.append(f"{names[k]}: " + ", ".join(groups[k]))
    return "\n".join(parts)


SMOOTH_RULES = """You turn a machine's literal reading of a sentence in a made-up language into natural, fluent English. \
You are given, for each sentence, the made-up text, a word-by-word gloss (stems and endings in capitals, e.g. dog-ACC means \
the dog as object), and a literal reading in simple English. The literal reading can be wrong where the language leaves information out \
(tense, who did what, plural, definiteness); use the gloss and ordinary sense to fix it. Some words in the gloss list alternatives after a slash: \
choose the one that makes sense. Words marked ? are names. Do not add facts. Output one natural English sentence per input sentence, \
in order, one per line, with no numbering and no comments."""


class Reducer:
    def __init__(self, llm):
        self.llm = llm

    def reduce(self, actor, conlang_id: str, tr: LanguageTranslator, english: str, *, job_id=None) -> dict:
        english = english.strip()
        system = build_system(tr.V)
        usage, calls = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0, "cost_micro_usd": 0}, 0

        def call(messages):
            nonlocal calls
            r = self.llm.complete(actor, "translate.reduce", system=system, messages=messages, conlang_id=conlang_id,
                                  job_id=job_id, cache_system=True)
            calls += 1
            u = r.usage
            usage["input"] += u.input_tokens
            usage["output"] += u.output_tokens
            usage["cache_read"] += u.cache_read_tokens
            usage["cache_write"] += u.cache_write_tokens
            usage["cost_micro_usd"] += r.cost_micro_usd
            return r.text.strip()

        msgs = [Message("user", english)]
        text = call(msgs)
        rounds = 0
        while rounds < ROUNDS:
            doc, issues = parse(tr.V, text)
            issues += validate(doc, tr.V, tr.realizer.g)
            bad = unknown_words(issues)
            if not bad:
                break
            rounds += 1
            lines = []
            for w in bad:
                sug = tr.V.suggest(w)
                lines.append(f"- {w}" + (f" (maybe: {', '.join(sug)})" if sug else ""))
            msgs = msgs + [Message("assistant", text), Message(
                "user", "These words are not in the vocabulary:\n" + "\n".join(lines) +
                "\nRewrite the whole text using only allowed words. Replace each missing word with allowed words that mean "
                "nearly the same. Answer with the rewritten text only.")]
            text = call(msgs)
        return {"re_text": text, "rounds": rounds, "calls": calls, "usage": usage}


class Smoother:
    def __init__(self, llm):
        self.llm = llm

    def smooth(self, actor, conlang_id: str, sentences: list, *, job_id=None) -> dict:
        """sentences: [{"text": language text, "gloss": "dog-ACC ...", "literal": restricted English}]"""
        blocks = []
        for i, s in enumerate(sentences, 1):
            blocks.append(f"{i}. language: {s['text']}\n   gloss: {s['gloss']}\n   literal: {s['literal']}")
        r = self.llm.complete(actor, "translate.smooth", system=SMOOTH_RULES, prompt="\n".join(blocks),
                              conlang_id=conlang_id, job_id=job_id)
        lines = [l.strip() for l in r.text.strip().split("\n") if l.strip()]
        lines = [l.split(". ", 1)[1] if l[:1].isdigit() and ". " in l[:5] else l for l in lines]
        usage = {"input": r.usage.input_tokens, "output": r.usage.output_tokens, "cost_micro_usd": r.cost_micro_usd}
        return {"lines": lines, "usage": usage}
