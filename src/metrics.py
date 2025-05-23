# pylint: disable=protected-access
import json
import os
import subprocess
from functools import partial
from io import StringIO
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

    Gauge(
        "borg_last_backup_duration",
        "Duration of the last Borg backup",
        ["repository"],
        registry=registry,
    )

    Gauge(
        "borg_last_backup_files",
        "Amount of files contained in the last Borg backup",
        ["repository"],
        registry=registry,
    )

    Gauge(
        "borg_last_backup_deduplicated_compressed_size",
        "Size of the deduplicated and compressed last Borg backup",
        ["repository"],
        registry=registry,
    )

    Gauge(
        "borg_last_backup_compressed_size",
        "Size of the compressed last Borg backup",
        ["repository"],
        registry=registry,
    )

    Gauge(
        "borg_last_backup_size",
        "Size of the last Borg backup",
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
    # temporary workaround for https://github.com/borgbackup/borg/issues/7255 to be used together with `--bypass-lock`
    tmp_env = os.environ.copy()
    tmp_env["HOME"] = "/tmp/borgmatic-exporter-cache"
    tmp_env["BORG_UNKNOWN_UNENCRYPTED_REPO_ACCESS_IS_OK"] = "yes"

    borgmatic_configs = " -c ".join(borgmatic_configs)
    # Overall repo info and last archive only
    repos = run_command(
        f"borgmatic -c {borgmatic_configs} --verbosity -1 borg info --bypass-lock --json --last 1",
        tmp_env,
    )
    # All archives
    archives = run_command(
        f"borgmatic -c {borgmatic_configs} --verbosity -1 borg list --bypass-lock --json",
        tmp_env,
    )

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
            latest_archive = r["archives"][-1]

            # Last Backup Timestamp
            set_metric(
                registry=registry,
                metric="borg_last_backup_timestamp",
                labels=labels,
                value=arrow.get(latest_archive["end"])
                .replace(tzinfo="local")
                .timestamp(),
            )

            # Last Backup Duration
            set_metric(
                registry=registry,
                metric="borg_last_backup_duration",
                labels=labels,
                value=latest_archive["duration"],
            )

            # Last Backup number of files
            set_metric(
                registry=registry,
                metric="borg_last_backup_files",
                labels=labels,
                value=latest_archive["stats"]["nfiles"],
            )

            # Last Backup Deduplicated Compressed Size
            set_metric(
                registry=registry,
                metric="borg_last_backup_deduplicated_compressed_size",
                labels=labels,
                value=latest_archive["stats"]["deduplicated_size"],
            )

            # Last Backup Compressed Size
            set_metric(
                registry=registry,
                metric="borg_last_backup_compressed_size",
                labels=labels,
                value=latest_archive["stats"]["compressed_size"],
            )

            # Last Backup Size
            set_metric(
                registry=registry,
                metric="borg_last_backup_size",
                labels=labels,
                value=latest_archive["stats"]["original_size"],
            )


def json_multi_parse(fileobj, decoder=json.JSONDecoder(), buffersize=2048):
    """
    Parses the content of the file object to json and yields every found valid json.
    Can read valid json which is concatenated together (in combination not valid json).
    """
    buffer = ""
    for chunk in iter(partial(fileobj.read, buffersize), ""):
        buffer += chunk
        while buffer:
            try:
                result, index = decoder.raw_decode(buffer)
                yield result
                buffer = buffer[index:].lstrip()
            except ValueError:
                # Not enough data to decode, read more
                break


def run_command(command: str, command_env=os.environ.copy()) -> dict:
    """
    Execute command via the command line and load the output into dictionary.
    """
    with timy.Timer(command):
        result = subprocess.run(
            command.split(" "), check=True, stdout=subprocess.PIPE, env=command_env
        )
    output = result.stdout.decode("utf-8").strip()
    return list(json_multi_parse(StringIO(output)))
