"""``booski ai``: seeding the catalogue and the provider check. No test calls a real provider."""

import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from booski_core import cli
from booski_core.config import Settings
from booski_core.modules.ai.models import AiModel, AiTask

pytestmark = pytest.mark.db


@pytest.fixture
def cli_settings(monkeypatch: pytest.MonkeyPatch, db_settings: Settings) -> Settings:
    settings = db_settings.model_copy(update={"anthropic_api_key": None})
    monkeypatch.setattr(cli, "get_settings", lambda: settings)
    return settings


def test_seed_catalog_is_idempotent(migrated_db: Engine, cli_settings: Settings) -> None:
    assert cli.main(["ai", "seed-catalog"]) == 0
    assert cli.main(["ai", "seed-catalog"]) == 0
    with Session(migrated_db) as db:
        assert db.scalar(select(func.count()).select_from(AiModel)) == 3
        assert db.scalar(select(func.count()).select_from(AiTask)) == 7


def test_check_explains_a_missing_key(
    migrated_db: Engine, cli_settings: Settings, capsys: pytest.CaptureFixture[str]
) -> None:
    assert cli.main(["ai", "check"]) == 1
    assert "BOOSKI_ANTHROPIC_API_KEY" in capsys.readouterr().err


def test_check_reports_model_tokens_and_cost(
    migrated_db: Engine,
    cli_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from ai_fakes import FakeProvider

    fake = FakeProvider()
    monkeypatch.setattr(
        "booski_core.modules.ai.providers.build_providers", lambda settings: {"anthropic": fake}
    )
    assert cli.main(["ai", "check"]) == 0
    assert "Claude Haiku 5.5 answered: 12 input and 4 output tokens, $0.000003." in capsys.readouterr().out
    assert [call.model_key for call in fake.calls] == ["claude-haiku-5-5"]
