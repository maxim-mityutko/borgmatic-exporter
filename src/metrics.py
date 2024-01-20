# pylint: disable=protected-access
import json
import subprocess
from typing import Any

import arrow
import timy
from prometheus_client import CollectorRegistry, Gauge


def create_metrics(registry):
    Gauge(
        "borg_unique_size",
        "Uncompressed size of the Borg repository",
        ["repository"],
        registry=registry,
    )

    Gauge(
        "borg_total_size",
        "Total size of the Borg repository",
        ["repository"],
        registry=registry,
    )

    Gauge(
        "borg_total_backups",
        "Total number of Borg backups",
        ["repository"],
        registry=registry,
    )

    Gauge(
        "borg_last_backup_timestamp",
        "Timestamp of the last Borg backup",
        ["repository"],
        registry=registry,
    )

    return registry


def set_metric(
    registry: CollectorRegistry, metric: str, labels: dict, value: Any
) -> None:
    c = registry._names_to_collectors[metric]
    c.labels(**labels).set(value)


def collect(borgmatic_configs: list, registry):
    borgmatic_configs = " ".join(borgmatic_configs)
    repos = run_command(f"borgmatic info -c {borgmatic_configs} --json")

    for i in range(len(repos)):
        labels = {"repository": repos[i]["repository"]["location"]}

        # Unique Size
        set_metric(
            registry=registry,
            metric="borg_unique_size",
            labels=labels,
            value=repos[i]["cache"]["stats"]["unique_size"],
        )

        # Total Size
        set_metric(
            registry=registry,
            metric="borg_total_size",
            labels=labels,
            value=repos[i]["cache"]["stats"]["total_size"],
        )

        # Total Backups
        set_metric(
            registry=registry,
            metric="borg_total_backups",
            labels=labels,
            value=len(repos[i]["archives"]),
        )

        if len(repos[i]["archives"]) == 0:
            continue

        latest_archive = repos[i]["archives"][-1]
        # Last Backup Timestamp
        set_metric(
            registry=registry,
            metric="borg_last_backup_timestamp",
            labels=labels,
            value=arrow.get(latest_archive["end"]).replace(tzinfo="local").timestamp(),
        )


def run_command(command: str) -> dict:
    """
    Execute command via the command line and load the output into dictionary.
    """
    with timy.Timer(command):
        result = subprocess.run(
            command.split(" "),
            check=True,
            stdout=subprocess.PIPE,
        )
    output = result.stdout.decode("utf-8").strip()
    return json.loads(output)
