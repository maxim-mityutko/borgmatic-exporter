import subprocess

import click
from loguru import logger
from prometheus_client import CollectorRegistry
from timy.settings import timy_config

from src.http_server import start_http_server

# https://github.com/pallets/click/issues/448#issuecomment-246029304
click.core._verify_python3_env = lambda: None  # pylint: disable=protected-access


def config_opt(func):
    return click.option(
        "-c",
        "--config",
        default=["/etc/borgmatic.d/config.yml"],
        help="The path to the borgmatic config file",
        multiple=True,
        type=click.Path(
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
        ),
        envvar="BORGMATIC_CONFIG",
    )(func)


@click.group()
def cli():
    pass


@cli.command()
@config_opt
@click.option(
    "--port",
    type=int,
    default=9996,
    show_default=True,
    help="The port the exporter will listen on",
    envvar="BORGMATIC_EXPORTER_PORT",
)
@click.option(
    "--time-borgmatic/--no-time-borgmatic",
    default=False,
    show_default=True,
    help="Show the time each Borgmatic call takes",
    envvar="BORGMATIC_EXPORTER_TIME",
)
def run(config, port, time_borgmatic):
    logger.info("Exporter execution parameters set...")
    logger.info(f"Borgmatic config path: {config}")
    logger.info(f"Port:'{port}'")
    registry = CollectorRegistry(auto_describe=True)
    timy_config.tracking = time_borgmatic
    start_http_server(config, registry, port)


def run_abort(cmd):
    try:
        subprocess.run(cmd.split(), check=True)
    except subprocess.CalledProcessError as ex:
        raise click.Abort() from ex
