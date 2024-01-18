import os
from click.testing import CliRunner

from src import cli

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


# noinspection PyTypeChecker
def test_cli_run_w_default_config():
    runner = CliRunner()
    result = runner.invoke(cli.run)
    assert "File '/etc/borgmatic.d/config.yml' does not exist." in result.output


# noinspection PyTypeChecker
def test_cli_run_w_not_set_config():
    runner = CliRunner()
    result = runner.invoke(cli.run, ["-c"])
    assert "Option '-c' requires an argument." in result.output


# noinspection PyTypeChecker
def test_cli_run_w_config(mocker):
    runner = CliRunner()
    mocker.patch("src.http_server.serve")
    result = runner.invoke(cli.run, ["-c", f"{PROJECT_ROOT}/data/config.yml"])
    assert result.exit_code == 0
