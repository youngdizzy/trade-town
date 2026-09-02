"""Covers the health endpoint's is_default_dev_save signal — CEO
directive "Paper Burn-in Test-Isolation Hardening." This is the one
real, non-secret signal frontend/tests/global-setup.ts reads before
running any Playwright test, to refuse to run against the shared
default dev save (the same save a paper-trading burn-in depends on).
Getting the boolean or its camelCase serialization wrong here would
silently defeat that whole protection.
"""
from __future__ import annotations

import pytest

from app.config import DEFAULT_DATABASE_URL, Settings
from app.schemas import HealthResponse


class TestDefaultDatabaseUrlDetection:
    def test_settings_with_no_env_override_matches_the_default_constant(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Settings.database_url's own default_factory reads DATABASE_URL,
        # falling back to DEFAULT_DATABASE_URL — a fresh Settings() with
        # no env override must equal the constant the health check
        # compares against, or the whole signal is wrong for every real
        # developer/burn-in run that never sets DATABASE_URL at all.
        monkeypatch.delenv("DATABASE_URL", raising=False)
        assert Settings().database_url == DEFAULT_DATABASE_URL

    def test_an_explicit_isolated_database_url_is_recognized_as_not_default(self) -> None:
        settings = Settings(database_url="sqlite:////tmp/isolated-test-save.db")
        assert settings.database_url != DEFAULT_DATABASE_URL

    def test_the_default_database_url_is_recognized_as_default(self) -> None:
        settings = Settings(database_url=DEFAULT_DATABASE_URL)
        assert settings.database_url == DEFAULT_DATABASE_URL


class TestHealthResponseSerialization:
    def test_is_default_dev_save_true_serializes_camel_case(self) -> None:
        response = HealthResponse(is_default_dev_save=True)
        dumped = response.model_dump(by_alias=True)
        assert dumped["isDefaultDevSave"] is True
        assert "is_default_dev_save" not in dumped

    def test_is_default_dev_save_false_serializes_camel_case(self) -> None:
        response = HealthResponse(is_default_dev_save=False)
        dumped = response.model_dump(by_alias=True)
        assert dumped["isDefaultDevSave"] is False

    def test_status_field_unchanged(self) -> None:
        response = HealthResponse(is_default_dev_save=False)
        assert response.status == "ok"
