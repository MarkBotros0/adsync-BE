"""Lightweight in-process sentiment classifier for IG comments and FB messages.

Lexicon-based — zero external deps, zero network calls. Not as accurate as an LLM but
good enough to colour comment chips green/red/grey at scale and aggregate to a brand
sentiment %. When budget for a hosted classifier shows up later the only thing that
needs to change is this module's ``classify`` signature.

Sources of the wordlists: a curated subset of the AFINN-165 + Bing Liu's opinion
lexicon, trimmed to the highest-frequency words to keep the module small.
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any, Literal

Sentiment = Literal["positive", "negative", "neutral"]


# Negation prefixes flip the polarity of the next ≤2 tokens.
_NEGATIONS: frozenset[str] = frozenset({
    "not", "no", "never", "none", "nobody", "nothing", "nowhere",
    "hardly", "scarcely", "barely", "doesn't", "isn't", "wasn't",
    "shouldn't", "wouldn't", "couldn't", "won't", "can't", "don't",
    "didn't", "haven't", "hasn't", "ain't", "without",
})

_POSITIVE: frozenset[str] = frozenset({
    "love", "loved", "loves", "loving", "amazing", "awesome", "incredible",
    "great", "good", "best", "beautiful", "fantastic", "perfect", "wonderful",
    "excellent", "brilliant", "happy", "thanks", "thank", "thankful",
    "grateful", "appreciate", "enjoy", "enjoyed", "favourite", "favorite",
    "stunning", "gorgeous", "fab", "fabulous", "delight", "delightful",
    "yes", "yay", "wow", "nice", "cute", "lovely", "kind", "friendly",
    "recommend", "recommended", "recommendation", "fast", "smooth", "easy",
    "helpful", "support", "solid", "strong", "winner", "win", "winning",
    "fire", "lit", "goat", "iconic", "queen", "king", "legend", "vibes",
    "obsessed", "crushing", "stunning", "glowing", "elite", "killer",
    "bomb", "slay", "slayed", "slaying", "perfection", "masterpiece",
    "satisfied", "satisfying", "pleased", "pleasure", "joy", "joyful",
    "smile", "smiled", "laugh", "laughing", "fun", "exciting", "excited",
    "interesting", "impressive", "impressed", "powerful", "innovative",
    "yes", "yeah", "yep", "yass", "yas",
})

_NEGATIVE: frozenset[str] = frozenset({
    "hate", "hated", "hating", "awful", "terrible", "horrible", "worst",
    "bad", "boring", "annoying", "annoyed", "annoy", "useless", "pointless",
    "garbage", "trash", "junk", "stupid", "dumb", "idiot", "ugly", "sad",
    "angry", "mad", "furious", "disappointed", "disappointing", "disappoint",
    "rubbish", "broken", "broke", "fail", "failed", "failing", "failure",
    "shit", "crap", "damn", "wtf", "fuck", "fucked", "fucking",
    "expensive", "overpriced", "rip-off", "scam", "fraud", "lying", "liar",
    "ignored", "ignore", "ignoring", "rude", "unprofessional", "unhelpful",
    "delay", "delayed", "late", "lost", "missing", "wrong", "error",
    "problem", "problems", "issue", "issues", "complaint", "complain",
    "refund", "cancel", "cancelled", "regret", "wasted", "waste",
    "unhappy", "miserable", "frustrated", "frustrating", "confused",
    "confusing", "difficult", "hard", "slow", "laggy", "laggy", "broken",
    "buggy", "glitchy", "crash", "crashed", "crashing", "freeze", "frozen",
    "no", "nope", "never",
})


_WORD_RE = re.compile(r"[a-z']+")
_EMOJI_POS = frozenset({"❤", "😍", "😊", "😁", "🥰", "😄", "🔥", "💯", "👏", "🙌", "👍"})
_EMOJI_NEG = frozenset({"😡", "😠", "😢", "😭", "😞", "👎", "🤮", "💩"})


def _tokenize(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


def _emoji_score(text: str) -> int:
    score = 0
    for ch in text:
        if ch in _EMOJI_POS:
            score += 1
        elif ch in _EMOJI_NEG:
            score -= 1
    return score


def score(text: str) -> int:
    """Signed integer score for ``text``. ``> 0`` is positive, ``< 0`` is negative.

    The magnitude is the number of polarised tokens net of negations and emoji.
    """
    if not text:
        return 0

    tokens = _tokenize(text)
    s = 0
    flip = 0  # how many upcoming tokens to negate (set to 2 after a negation)
    for tok in tokens:
        delta = 0
        if tok in _POSITIVE:
            delta = 1
        elif tok in _NEGATIVE:
            delta = -1

        if flip > 0:
            delta = -delta
            flip -= 1

        if tok in _NEGATIONS:
            flip = 2  # negate next two content words
            continue

        s += delta

    s += _emoji_score(text)
    return s


def classify(text: str) -> Sentiment:
    """Convert a raw text to one of ``positive`` / ``negative`` / ``neutral``."""
    s = score(text)
    if s > 0:
        return "positive"
    if s < 0:
        return "negative"
    return "neutral"


def summarise(items: Iterable[dict[str, Any]], text_key: str = "text") -> dict[str, Any]:
    """Produce a {positive, neutral, negative, total, positive_pct} roll-up.

    ``items`` is any iterable of dicts; each must have ``text_key``. Mutates each item
    in place to add a ``sentiment`` field so the caller can render chips without
    a second pass.
    """
    counts = {"positive": 0, "neutral": 0, "negative": 0}
    seen = 0
    for item in items:
        cls = classify(item.get(text_key) or "")
        item["sentiment"] = cls
        counts[cls] += 1
        seen += 1
    pos_pct = round((counts["positive"] / seen) * 100, 2) if seen else 0.0
    neg_pct = round((counts["negative"] / seen) * 100, 2) if seen else 0.0
    return {
        "total": seen,
        "positive": counts["positive"],
        "neutral": counts["neutral"],
        "negative": counts["negative"],
        "positive_pct": pos_pct,
        "negative_pct": neg_pct,
    }
