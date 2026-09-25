"""
AI services — strictly advisory.

Provider interface with two implementations:
  - MockAIProvider: deterministic heuristics, no network. Default.
  - OpenAICompatibleProvider: optional, env-configured; privacy-scrubbed input.

Rules enforced here:
  - No workflow decision is ever made by AI alone.
  - Every recommendation is persisted with provider + confidence for review.
  - Text is scrubbed of obvious PII before any external call.
"""

import logging
import re

from django.conf import settings

from apps.ai.models import AIRecommendation

logger = logging.getLogger("safecity")

KEYWORD_CATEGORY_MAP = {
    "pothole": "road-damage",
    "road damage": "road-damage",
    "crater": "road-damage",
    "accident": "traffic-accident",
    "crash": "traffic-accident",
    "collision": "traffic-accident",
    "fire": "fire",
    "smoke": "fire",
    "flames": "fire",
    "flood": "flooding",
    "waterlog": "flooding",
    "waterlogging": "flooding",
    "garbage": "garbage-accumulation",
    "trash": "garbage-accumulation",
    "waste": "garbage-accumulation",
    "streetlight": "broken-streetlight",
    "street light": "broken-streetlight",
    "dark street": "broken-streetlight",
    "leak": "water-leakage",
    "pipe burst": "water-leakage",
    "wire": "electrical-hazard",
    "electric": "electrical-hazard",
    "transformer": "electrical-hazard",
    "unsafe": "public-safety-threat",
    "threat": "public-safety-threat",
    "stray": "stray-animal",
    "dog": "stray-animal",
    "cat": "stray-animal",
    "noise": "noise-complaint",
    "loud": "noise-complaint",
}

CRITICAL_WORDS = {
    "fire",
    "electrocution",
    "collapse",
    "explosion",
    "emergency",
    "danger",
    "life-threatening",
}
HIGH_WORDS = {"injury", "accident", "hazard", "flooding", "flood", "leak", "unsafe"}

VALID_SEVERITIES = {"low", "medium", "high", "critical"}

# Tokeniser for keyword matching (letters/digits only, lowercased by the caller).
WORD_RE = re.compile(r"[a-z0-9]+")
# Light suffix tolerance for plurals/gerunds: "wires", "flooded", "flooding",
# "leaky", "loudly", "electricity"… but never "cattle"/"fireplace"/"loudspeaker".
WORD_SUFFIXES = {"s", "es", "ed", "d", "ing", "ly", "y", "er", "ers", "est", "ity", "al"}


def _token_matches(keyword: str, token: str) -> bool:
    """Exact token, or the keyword plus a small plural/gerund-style suffix."""
    if token == keyword:
        return True
    if not token.startswith(keyword):
        return False
    return len(keyword) + 1 <= len(token) <= len(keyword) + 3 and token[len(keyword) :] in WORD_SUFFIXES


def _count_hits(keyword: str, text: str, tokens: list[str]) -> int:
    """
    Count keyword occurrences in a token-aware way.

    Phrase keywords ("road damage", "street light") stay substring matches on
    the whole text; single words only match whole tokens (with suffix slack),
    so "wire" no longer fires on "wiredrawn" or "gwale".
    """
    if " " in keyword:
        return text.count(keyword)
    return sum(1 for token in tokens if _token_matches(keyword, token))


def scrub_pii(text: str) -> str:
    """Remove obvious PII before any external AI call (phones, emails, tax IDs)."""
    text = re.sub(r"\+?\d[\d\s().-]{8,}\d", "[phone]", text)
    text = re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "[email]", text)
    text = re.sub(r"\b[A-Z]{5}\d{4}[A-Z]\b", "[vehicle-id]", text)
    text = re.sub(r"\b\d{12}\b", "[national-id]", text)
    return text


class MockAIProvider:
    """Deterministic keyword heuristics — no network, no data leaves the app."""

    name = "mock"

    def suggest_category(self, title: str, description: str) -> dict:
        text = f"{title} {description}".lower()
        tokens = WORD_RE.findall(text)
        best_slug, hits = None, 0
        for keyword, slug in KEYWORD_CATEGORY_MAP.items():
            count = _count_hits(keyword, text, tokens)
            if count > hits:
                best_slug, hits = slug, count
        confidence = min(0.35 + hits * 0.15, 0.95) if best_slug else 0.2
        return {"category_slug": best_slug, "confidence": round(confidence, 2)}

    def suggest_severity(self, description: str) -> dict:
        text = description.lower()
        if any(w in text for w in CRITICAL_WORDS):
            return {"severity": "critical", "confidence": 0.8}
        if any(w in text for w in HIGH_WORDS):
            return {"severity": "high", "confidence": 0.7}
        return {"severity": "medium", "confidence": 0.6}

    def summarize(self, description: str) -> dict:
        sentences = re.split(r"[.!?]\s+", description.strip())
        first = sentences[0][:200] if sentences else description[:200]
        return {"summary": first, "confidence": 0.9}

    def check_duplicates(self, title: str, description: str, candidates) -> dict:
        """Lexical overlap + proximity hint; final judgement stays human."""
        text = set(f"{title} {description}".lower().split())
        best, best_score = None, 0.0
        for candidate in candidates:
            ctext = set(f"{candidate.title} {candidate.description}".lower().split())
            if not text or not ctext:
                continue
            score = len(text & ctext) / len(text | ctext)
            if score > best_score:
                best, best_score = candidate, score
        return {
            "duplicate_of": str(best.id) if best and best_score > 0.45 else None,
            "similarity": round(best_score, 2),
        }


class OpenAICompatibleProvider:
    """
    Optional adapter for OpenAI-compatible APIs (OpenAI, vLLM, Ollama, LM Studio).

    Disabled unless OPENAI_API_KEY is set. Text sent externally is scrubbed of
    PII first (defense in depth — by default no external calls happen at all).
    """

    name = "openai-compatible"

    def __init__(self):
        self.api_key = settings.SAFECITY.get("OPENAI_API_KEY", "")
        self.base_url = settings.SAFECITY.get("OPENAI_BASE_URL", "https://api.openai.com/v1")

    def _available(self) -> bool:
        return bool(self.api_key)

    def _chat(self, system: str, user: str, json_mode: bool = True) -> dict:
        if not self._available():
            raise RuntimeError("AI provider not configured")
        import requests

        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": scrub_pii(user)},
                ],
                "temperature": 0.1,
                **({"response_format": {"type": "json_object"}} if json_mode else {}),
            },
            timeout=15,
        )
        response.raise_for_status()
        import json

        content = response.json()["choices"][0]["message"]["content"]
        return json.loads(content)

    def suggest_category(self, title: str, description: str) -> dict:
        result = self._chat(
            "Classify the city incident. Respond JSON: {category_slug, confidence}",
            f"Title: {title}\nDescription: {description}",
        )
        return {
            "category_slug": result.get("category_slug"),
            "confidence": float(result.get("confidence", 0.5)),
        }

    def suggest_severity(self, description: str) -> dict:
        result = self._chat(
            "Rate incident severity (low/medium/high/critical). Respond JSON: "
            "{severity, confidence}",
            description,
        )
        severity = str(result.get("severity", "")).strip().lower()
        if severity not in VALID_SEVERITIES:
            # Never trust a hallucinated value (e.g. "catastrophic") — fall
            # back to the deterministic mock heuristic instead.
            return MockAIProvider().suggest_severity(description)
        return {
            "severity": severity,
            "confidence": float(result.get("confidence", 0.5)),
        }

    def summarize(self, description: str) -> dict:
        result = self._chat(
            "Summarize in one sentence. Respond JSON: {summary}", description, json_mode=False
        )
        return {"summary": result.get("summary", ""), "confidence": 0.8}


def get_provider():
    """Return the configured provider; mock is the safe default."""
    name = settings.SAFECITY.get("AI_PROVIDER", "mock")
    if name == "openai-compatible":
        provider = OpenAICompatibleProvider()
        if provider._available():
            return provider
    return MockAIProvider()


def record_recommendation(
    *, incident, kind: str, output: dict, confidence=None, provider=None
) -> AIRecommendation:
    """Persist one AI recommendation for later human review."""
    provider = provider or get_provider()
    return AIRecommendation.objects.create(
        incident=incident,
        kind=kind,
        provider=provider.name,
        output=output,
        confidence=confidence,
    )
