import subprocess
from pathlib import Path

import click
from click.core import ParameterSource
from loguru import logger
from prometheus_client import CollectorRegistry
from timy.settings import timy_config

from src.http_server import start_http_server

# https://github.com/pallets/click/issues/448#issuecomment-246029304
click.core._verify_python3_env = lambda: None  # pylint: disable=protected-access


def _explicitly_set(ctx: click.Context, name: str) -> bool:
    source = ctx.get_parameter_source(name)
    return source is not None and source is not ParameterSource.DEFAULT


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
    "--unix-socket",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    show_default=True,
    help="Path of the UNIX socket to listen on instead of a TCP socket. Cannot be combined with --host or --port.",
    envvar="BORGMATIC_EXPORTER_UNIX_SOCKET",
)
@click.option(
    "--unix-socket-mode",
    type=str,
    default=None,
    show_default=True,
    help="The unix permission for the UNIX socket.",
    envvar="BORGMATIC_EXPORTER_UNIX_SOCKET_MODE",
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
@click.pass_context
def run(
    ctx: click.Context,
    config,
    host,
    port,
    unix_socket,
    unix_socket_mode,
    time_borgmatic,
    cache_timeout,
):
    if unix_socket is not None:
        clashes = [n for n in ("host", "port") if _explicitly_set(ctx, n)]
        if clashes:
            opts = " or ".join(f"--{n.replace('_', '-')}" for n in clashes)
            raise click.UsageError(
                f"--unix-socket cannot be combined with {opts}.", ctx=ctx
            )

    if unix_socket_mode is not None and unix_socket is None:
        logger.info(
            "The mode how the unix socket should be created is set, but no unix socket configuration was supplied."
        )

    logger.info("Exporter execution parameters set...")
    logger.info(f"Borgmatic config path: {config}")
    logger.info(f"Host:'{host}'")
    logger.info(f"Port:'{port}'")
    logger.info(f"Unix Socket:'{unix_socket}'")
    logger.info(f"Unix Socket Mode:'{unix_socket_mode}'")
    logger.info(f"Cache timeout (seconds):'{cache_timeout}'")
    registry = CollectorRegistry(auto_describe=True)
    timy_config.tracking = time_borgmatic
    start_http_server(
        config,
        registry,
        host,
        port,
        unix_socket,
        unix_socket_mode,
        cache_timeout,
    )


def run_abort(cmd):
    try:
        subprocess.run(cmd.split(), check=True)
    except subprocess.CalledProcessError as ex:
        raise click.Abort() from ex
