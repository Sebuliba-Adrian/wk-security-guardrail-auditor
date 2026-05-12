"""
Unit tests — AIAnalyser
Phase: RED — all tests must FAIL before implementation exists.

INTENT: Produce an executive summary when an AI key is available,
gracefully return None when it is not.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.scanner.engine import Finding


def _finding(rule_id: str, severity: str) -> Finding:
    return Finding(
        rule_id=rule_id,
        severity=severity,  # type: ignore[arg-type]
        title="title",
        description="desc",
        remediation="fix it",
        resource_name="res",
        resource_type="aws_test",
    )


# ---------------------------------------------------------------------------
# Graceful skip — no key set
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_given_no_api_key_when_analysed_then_returns_none() -> None:
    from app.scanner.ai_analyser import AIAnalyser

    with patch("app.scanner.ai_analyser.settings") as mock_settings:
        mock_settings.openai_api_key = ""
        mock_settings.gemini_api_key = ""
        result = await AIAnalyser.summarise(
            findings=[_finding("S3_PUBLIC_ACL", "CRITICAL")],
            filename="main.tf",
            risk_score=40,
        )
    assert result is None


# ---------------------------------------------------------------------------
# OpenAI path — key present, API called
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_given_openai_key_when_analysed_then_returns_string() -> None:
    from app.scanner.ai_analyser import AIAnalyser

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Critical: S3 bucket is public. Fix ACL immediately."

    with patch("app.scanner.ai_analyser.settings") as mock_settings:
        mock_settings.openai_api_key = "sk-test-key"
        mock_settings.gemini_api_key = ""
        with patch("app.scanner.ai_analyser.AsyncOpenAI") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

            result = await AIAnalyser.summarise(
                findings=[_finding("S3_PUBLIC_ACL", "CRITICAL")],
                filename="main.tf",
                risk_score=40,
            )

    assert isinstance(result, str)
    assert len(result) > 0


# ---------------------------------------------------------------------------
# Gemini path — Gemini key present, OpenAI-compatible endpoint used
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_given_gemini_key_when_analysed_then_returns_string() -> None:
    from app.scanner.ai_analyser import AIAnalyser

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Gemini summary: 2 issues found."

    with patch("app.scanner.ai_analyser.settings") as mock_settings:
        mock_settings.openai_api_key = ""
        mock_settings.gemini_api_key = "AIza-test-key"
        with patch("app.scanner.ai_analyser.AsyncOpenAI") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

            result = await AIAnalyser.summarise(
                findings=[_finding("UNENCRYPTED_EBS", "HIGH")],
                filename="infra.tf",
                risk_score=20,
            )

    assert isinstance(result, str)
    assert len(result) > 0


# ---------------------------------------------------------------------------
# API failure — gracefully returns None, never raises
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_given_api_error_when_analysed_then_returns_none() -> None:
    from app.scanner.ai_analyser import AIAnalyser

    with patch("app.scanner.ai_analyser.settings") as mock_settings:
        mock_settings.openai_api_key = "sk-test-key"
        mock_settings.gemini_api_key = ""
        with patch("app.scanner.ai_analyser.AsyncOpenAI") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            mock_client.chat.completions.create = AsyncMock(
                side_effect=Exception("API unavailable")
            )

            result = await AIAnalyser.summarise(
                findings=[_finding("S3_PUBLIC_ACL", "CRITICAL")],
                filename="main.tf",
                risk_score=40,
            )

    assert result is None


# ---------------------------------------------------------------------------
# Empty findings — still calls AI (score may be zero but file was clean)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_given_empty_findings_when_analysed_then_returns_string() -> None:
    from app.scanner.ai_analyser import AIAnalyser

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "No issues found. Configuration is compliant."

    with patch("app.scanner.ai_analyser.settings") as mock_settings:
        mock_settings.openai_api_key = "sk-test-key"
        mock_settings.gemini_api_key = ""
        with patch("app.scanner.ai_analyser.AsyncOpenAI") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

            result = await AIAnalyser.summarise(
                findings=[],
                filename="clean.tf",
                risk_score=0,
            )

    assert isinstance(result, str)
