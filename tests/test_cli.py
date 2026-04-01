import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from cli.run import cli


@pytest.fixture
def runner():
    return CliRunner()


def test_scrape_command_triggers_celery_task(runner):
    with patch("cli.run.scrape_city_task") as mock_task:
        mock_task.delay.return_value = MagicMock(id="fake-task-id")

        with patch("cli.run.SessionLocal") as mock_sl:
            mock_run = MagicMock()
            mock_run.id = "fake-run-id"
            mock_sl.return_value.__enter__ = MagicMock(return_value=MagicMock())
            mock_sl.return_value.__exit__ = MagicMock(return_value=False)

            result = runner.invoke(cli, ["scrape", "--city", "Houston", "--state", "TX"])

    assert result.exit_code == 0
    assert "Houston" in result.output


def test_scrape_command_requires_city(runner):
    result = runner.invoke(cli, ["scrape", "--state", "TX"])
    assert result.exit_code != 0


def test_scrape_command_requires_state(runner):
    result = runner.invoke(cli, ["scrape", "--city", "Houston"])
    assert result.exit_code != 0


def test_status_command_not_found(runner):
    import uuid
    with patch("cli.run.SessionLocal") as mock_sl:
        mock_db = MagicMock()
        mock_db.query.return_value.filter_by.return_value.first.return_value = None
        mock_sl.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_sl.return_value.__exit__ = MagicMock(return_value=False)
        result = runner.invoke(cli, ["status", "--run-id", str(uuid.uuid4())])
    assert "not found" in result.output.lower() or result.exit_code != 0


def test_cli_help(runner):
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "scrape" in result.output
    assert "status" in result.output
    assert "export" in result.output
