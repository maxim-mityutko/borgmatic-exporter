# pylint: disable=protected-access
import json
import subprocess
from typing import Any

import arrow
import timy
from prometheus_client import CollectorRegistry, Gauge


def create_metrics(registry):
    Gauge(
        "borg_total_backups",
        "Total number of Borg backups",
        ["repository"],
        registry=registry,
    )

    Gauge(
        "borg_total_chunks",
        "Number of chunks in the Borg repository",
        ["repository"],
        registry=registry,
    )

    Gauge(
        "borg_total_compressed_size",
        "Total compressed size of the Borg repository",
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
        "borg_total_deduplicated_compressed_size",
        "Total size of the deduplicated and compressed Borg repository",
        ["repository"],
        registry=registry,
    )

    Gauge(
        "borg_total_deduplicated_size",
        "Uncompressed size of the Borg repository",
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
    borgmatic_configs = " -c ".join(borgmatic_configs)
    # Overall repo info and last archive only
    repos = run_command(f"borgmatic info -c {borgmatic_configs} --json --last 1")
    # All archives
    archives = run_command(f"borgmatic list -c {borgmatic_configs} --json")

    for r, a in zip(repos, archives):
        labels = {"repository": r["repository"]["location"]}

        # Total Backups
        set_metric(
            registry=registry,
            metric="borg_total_backups",
            labels=labels,
            value=len(a.get("archives", [])),
        )

        # Total Chunks
        set_metric(
            registry=registry,
            metric="borg_total_chunks",
            labels=labels,
            value=r["cache"]["stats"]["total_chunks"],
        )

        # Compressed Size
        set_metric(
            registry=registry,
            metric="borg_total_compressed_size",
            labels=labels,
            value=r["cache"]["stats"]["total_csize"],
        )

        # Total Size
        set_metric(
            registry=registry,
            metric="borg_total_size",
            labels=labels,
            value=r["cache"]["stats"]["total_size"],
        )

        # Total Deduplicated Compressed Size
        set_metric(
            registry=registry,
            metric="borg_total_deduplicated_compressed_size",
            labels=labels,
            value=r["cache"]["stats"]["unique_csize"],
        )

        # Total Deduplicated Size
        set_metric(
            registry=registry,
            metric="borg_total_deduplicated_size",
            labels=labels,
            value=r["cache"]["stats"]["unique_size"],
        )

        if r.get("archives") and len(r["archives"]) > 0:
            # Last Backup Timestamp
            latest_archive = r["archives"][-1]
            set_metric(
                registry=registry,
                metric="borg_last_backup_timestamp",
                labels=labels,
                value=arrow.get(latest_archive["end"])
                .replace(tzinfo="local")
                .timestamp(),
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
