import subprocess

import click
from loguru import logger
from pathlib import Path
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
            dir_okay=True,
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
    "--host",
    type=str,
    default="0.0.0.0",
    show_default=True,
    help="The host the exporter will listen on",
    envvar="BORGMATIC_EXPORTER_HOST",
)
@click.option(
    "--time-borgmatic/--no-time-borgmatic",
    default=False,
    show_default=True,
    help="Show the time each Borgmatic call takes",
    envvar="BORGMATIC_EXPORTER_TIME",
)
@click.option(
    "--cache-timeout",
    type=int,
    default=600,
    show_default=True,
    help="Cache the response of the metrics endpoint for the given number of seconds, set to 0 to disable caching",
    envvar="BORGMATIC_EXPORTER_CACHE_TIMEOUT",
)
@click.option(
    "--borg-home",
    type=click.Path(file_okay=False, writable=True, resolve_path=True, path_type=Path),
    default=Path("/tmp/borgmatic-exporter-cache"),
    show_default=True,
    help="The directory borg will use as its home.",
    envvar="BORGMATIC_EXPORTER_BORG_HOME",
)
def run(config, host, port, time_borgmatic, cache_timeout, borg_home):
    logger.info("Exporter execution parameters set...")
    logger.info(f"Borgmatic config path: {config}")
    logger.info(f"Host:'{host}'")
    logger.info(f"Port:'{port}'")
    logger.info(f"Cache timeout (seconds):'{cache_timeout}'")
    logger.info(f"Borg home:'{borg_home}'")
    registry = CollectorRegistry(auto_describe=True)
    timy_config.tracking = time_borgmatic
    start_http_server(config, registry, host, port, cache_timeout, borg_home)


def run_abort(cmd):
    try:
        subprocess.run(cmd.split(), check=True)
    except subprocess.CalledProcessError as ex:
        raise click.Abort() from ex
