"""Local structured JSON generation for generic documents."""

from __future__ import annotations

import json
import os
import re
import subprocess  # nosec B404 - used only for optional local Ollama runtime.
from collections import Counter

from pydantic import BaseModel, Field

from src.slm import run_slm


class StructuredDocument(BaseModel):
    """Schema required by the generic StructIt workflow."""

    title: str = ""
    people: list[str] = Field(default_factory=list)
    organizations: list[str] = Field(default_factory=list)
    emails: list[str] = Field(default_factory=list)
    phones: list[str] = Field(default_factory=list)
    dates: list[str] = Field(default_factory=list)
    summary: str = ""
    keywords: list[str] = Field(default_factory=list)


SYSTEM_PROMPT = """You extract structured information from documents.
Return only valid JSON with exactly these keys:
title, people, organizations, emails, phones, dates, summary, keywords.
Do not invent facts. Use empty strings or empty lists when unknown."""

USER_PROMPT_TEMPLATE = """Extract structured JSON from this document:

{text}

JSON schema:
{schema}
"""

EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
PHONE_PATTERN = re.compile(
    r"(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{3,5}\)?[\s.-]?)?\d{3,5}[\s.-]?\d{4}"
)
DATE_PATTERN = re.compile(
    r"\b(?:\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2}|"
    r"\d{1,2}\s+[A-Za-z]{3,9}\s+\d{2,4})\b"
)
STOP_WORDS = {
    "about",
    "after",
    "also",
    "and",
    "are",
    "from",
    "have",
    "into",
    "that",
    "the",
    "this",
    "with",
    "your",
    "will",
    "for",
    "not",
    "you",
}


def structure_text(
    text: str,
    runtime: str | None = None,
) -> tuple[dict, str, list[str]]:
    """
    Convert normalized text to the generic structured JSON schema.

    Returns structured JSON, status, and logs. The function tries a configured
    local model runtime first and always falls back to deterministic extraction.
    """
    logs: list[str] = []
    runtime_name = runtime or os.getenv("STRUCTIT_LLM_RUNTIME") or "none"
    if runtime_name != "none":
        model_result = _try_local_model(text, runtime_name, logs)
        if model_result:
            logs.append(f"Structured with local model runtime: {runtime_name}.")
            return model_result, _status_for(model_result), logs

    logs.append("Structured with deterministic local extractor.")
    structured = _structure_with_rules(text)
    return structured, _status_for(structured), logs


def _try_local_model(text: str, runtime: str, logs: list[str]) -> dict | None:
    if runtime == "llama.cpp":
        return _try_llama_cpp(text, logs)
    if runtime == "ollama":
        return _try_ollama(text, logs)

    logs.append(f"Unknown local model runtime '{runtime}', using fallback.")
    return None


def _try_llama_cpp(text: str, logs: list[str]) -> dict | None:
    prompt = USER_PROMPT_TEMPLATE.format(
        text=text[:4000],
        schema=json.dumps(StructuredDocument.model_json_schema()),
    )
    try:
        raw = run_slm(prompt, SYSTEM_PROMPT)
        return _validate_json(raw)
    except Exception as exc:
        logs.append(f"llama.cpp unavailable: {exc}")
        return None


def _try_ollama(text: str, logs: list[str]) -> dict | None:
    model = os.getenv("STRUCTIT_OLLAMA_MODEL", "llama3.2:3b")
    prompt = USER_PROMPT_TEMPLATE.format(
        text=text[:4000],
        schema=json.dumps(StructuredDocument.model_json_schema()),
    )
    try:
        result = subprocess.run(  # nosec B603 B607 - local Ollama executable only.
            ["ollama", "run", model, prompt],
            check=False,
            capture_output=True,
            text=True,
            timeout=90,
        )
    except Exception as exc:
        logs.append(f"Ollama unavailable: {exc}")
        return None

    if result.returncode != 0:
        logs.append(f"Ollama returned exit code {result.returncode}.")
        return None
    return _validate_json(result.stdout)


def _validate_json(raw_output: str) -> dict | None:
    clean = raw_output.strip()
    start = clean.find("{")
    end = clean.rfind("}")
    if start >= 0 and end >= start:
        clean = clean[start : end + 1]
    try:
        parsed = json.loads(clean)
    except json.JSONDecodeError:
        return None
    return StructuredDocument(**parsed).model_dump(mode="json")


def _structure_with_rules(text: str) -> dict:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    title = lines[0][:120] if lines else ""
    emails = sorted(set(EMAIL_PATTERN.findall(text)))
    phones = sorted(
        set(match.group(0).strip() for match in PHONE_PATTERN.finditer(text))
    )
    dates = sorted(set(DATE_PATTERN.findall(text)))
    organizations = _extract_organizations(text)
    people = _extract_people(text, organizations)
    keywords = _extract_keywords(text)

    return StructuredDocument(
        title=title,
        people=people,
        organizations=organizations,
        emails=emails,
        phones=phones,
        dates=dates,
        summary=_summarize(text),
        keywords=keywords,
    ).model_dump(mode="json")


def _extract_people(text: str, organizations: list[str]) -> list[str]:
    candidates = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2}\b", text)
    blocked = set(organizations)
    return _unique_limited(
        [candidate for candidate in candidates if candidate not in blocked]
    )


def _extract_organizations(text: str) -> list[str]:
    patterns = [
        r"\b[A-Z][A-Za-z&.\- ]+\s(?:Ltd|Limited|Inc|LLC|Corp|Company|Hospital)\b",
        r"\b[A-Z][A-Za-z&.\- ]+\s(?:University|College|School|Bank)\b",
    ]
    matches: list[str] = []
    for pattern in patterns:
        matches.extend(re.findall(pattern, text))
    return _unique_limited(matches)


def _extract_keywords(text: str) -> list[str]:
    words = [
        word.lower()
        for word in re.findall(r"\b[A-Za-z][A-Za-z0-9-]{3,}\b", text)
        if word.lower() not in STOP_WORDS
    ]
    return [word for word, _ in Counter(words).most_common(12)]


def _summarize(text: str) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    summary = " ".join(sentence for sentence in sentences[:3] if sentence)
    return summary[:600]


def _unique_limited(values: list[str], limit: int = 20) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        cleaned = re.sub(r"\s+", " ", value).strip(" ,.-")
        if cleaned and cleaned not in seen:
            output.append(cleaned)
            seen.add(cleaned)
        if len(output) >= limit:
            break
    return output


def _status_for(structured: dict) -> str:
    if structured.get("summary") or structured.get("emails") or structured.get("dates"):
        return "success"
    if any(
        structured.get(key) for key in ("title", "people", "organizations", "keywords")
    ):
        return "partial"
    return "failed"
