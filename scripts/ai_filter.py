"""Shared helper: decide whether a headline is actually about AI.

General tech feeds (BBC Technology, CNBC, The Verge, Wired...) carry plenty of
non-AI news, and a publication called AI Pulse must not lead with a GTA 6
story. Everything that presents itself as AI news filters through this.
"""

import re

AI_RE = re.compile(
    r"\b(ai|a\.i\.|artificial intelligence|llms?|gpt-?[0-9]*|chatgpt|claude|gemini|"
    r"openai|anthropic|nvidia|machine learning|neural|chatbots?|agentic|agents?|"
    r"models?|inference|transformer|deepmind|mistral|copilot|diffusion|robots?|"
    r"gpus?|datacent(?:er|re)|foundation model|generative)\b",
    re.IGNORECASE,
)


def is_ai_story(item):
    """True when the title (or summary, if present) mentions AI."""
    text = " ".join(str(item.get(k, "")) for k in ("title", "summary", "description"))
    return bool(AI_RE.search(text))
