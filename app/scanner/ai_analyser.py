"""AIAnalyser — optional executive summary via OpenAI or Gemini.

Gracefully returns None if no API key is configured or if the API call fails.
Gemini is accessed via its OpenAI-compatible endpoint — one SDK, two providers.
"""

from __future__ import annotations

from openai import AsyncOpenAI

from app.core.config import settings
from app.scanner.engine import Finding

_OPENAI_BASE_URL = "https://api.openai.com/v1"
_OPENAI_MODEL = "gpt-4o-mini"

_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
_GEMINI_MODEL = "models/gemini-2.0-flash-lite"

_DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
_DEEPSEEK_MODEL = "deepseek-chat"

_SYSTEM_PROMPT = (
    "You are a cloud security expert. Analyse the IaC scan findings below and produce "
    "a concise executive summary (3-5 sentences). Lead with the overall risk level, "
    "name the top 3 most critical issues with their resource names, and end with one "
    "clear recommended first action. Be direct and specific — no filler text."
)


class AIAnalyser:
    @staticmethod
    async def summarise(
        findings: list[Finding],
        filename: str,
        risk_score: int,
    ) -> str | None:
        api_key, base_url, model = AIAnalyser._resolve_provider()
        if not api_key:
            return None

        user_content = AIAnalyser._build_prompt(findings, filename, risk_score)
        try:
            client = AsyncOpenAI(api_key=api_key, base_url=base_url)
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                max_tokens=300,
                temperature=0.3,
            )
            return response.choices[0].message.content or None
        except Exception:
            return None

    @staticmethod
    def _resolve_provider() -> tuple[str, str, str]:
        if settings.openai_api_key:
            return settings.openai_api_key, _OPENAI_BASE_URL, _OPENAI_MODEL
        if settings.gemini_api_key:
            return settings.gemini_api_key, _GEMINI_BASE_URL, _GEMINI_MODEL
        if settings.deepseek_api_key:
            return settings.deepseek_api_key, _DEEPSEEK_BASE_URL, _DEEPSEEK_MODEL
        return "", _OPENAI_BASE_URL, _OPENAI_MODEL

    @staticmethod
    def _build_prompt(findings: list[Finding], filename: str, risk_score: int) -> str:
        if not findings:
            return (
                f"File: {filename}\nRisk score: {risk_score}/100\n"
                "Findings: None — the file passed all security checks."
            )
        lines = [f"File: {filename}", f"Risk score: {risk_score}/100", "Findings:"]
        for f in findings:
            lines.append(
                f"  [{f.severity}] {f.rule_id} — {f.resource_type}/{f.resource_name}: {f.title}"
            )
        return "\n".join(lines)
