import json
import os

import arrow
import pytest
from prometheus_client import CollectorRegistry

from src import metrics

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture(scope="function")
def registry():
    registry = CollectorRegistry(auto_describe=True)
    yield registry


@pytest.fixture(scope="function")
def mock_run_command(mocker):
    with open(f"{PROJECT_ROOT}/data/repo-info.json") as j:
        ri = json.load(j)

    yield mocker.patch("src.metrics.run_command", return_value=ri)


def test_run_command():
    result = metrics.run_command(command='echo {"foo": "bar"}')
    assert result == {"foo": "bar"}


def test_registry(registry):
    result = metrics.create_metrics(registry=registry)._names_to_collectors
    assert "borg_total_backups" in result
    assert "borg_total_chunks" in result
    assert "borg_total_compressed_size" in result
    assert "borg_total_size" in result
    assert "borg_total_deduplicated_compressed_size" in result
    assert "borg_total_deduplicated_size" in result
    assert "borg_last_backup_timestamp" in result


def test_collect(registry, mock_run_command):
    metrics.create_metrics(registry=registry)
    metrics.collect(
        borgmatic_configs=["/conf/foo.yaml", "/conf/bar.yaml"], registry=registry
    )

    total_backups = registry.get_sample_value(
        "borg_total_backups", labels={"repository": "/borg/backup-1"}
    )
    assert total_backups == 2.0

    total_chunks = registry.get_sample_value(
        "borg_total_chunks", labels={"repository": "/borg/backup-1"}
    )
    assert total_chunks == 3505.0

    total_compressed_size = registry.get_sample_value(
        "borg_total_compressed_size", labels={"repository": "/borg/backup-1"}
    )
    assert total_compressed_size == 3965903861.0

    total_size = registry.get_sample_value(
        "borg_total_size", labels={"repository": "/borg/backup-1"}
    )
    assert total_size == 8446787072.0

    total_deduplicated_compressed_size = registry.get_sample_value(
        "borg_total_deduplicated_compressed_size",
        labels={"repository": "/borg/backup-1"},
    )
    assert total_deduplicated_compressed_size == 537932015.0

    total_deduplicated_size_1 = registry.get_sample_value(
        "borg_total_deduplicated_size", labels={"repository": "/borg/backup-1"}
    )
    assert total_deduplicated_size_1 == 1296544339.0

    total_deduplicated_size_2 = registry.get_sample_value(
        "borg_total_deduplicated_size", labels={"repository": "/borg/backup-2"}
    )
    assert total_deduplicated_size_2 == 21296544339.0

    last_backup_timestamp = registry.get_sample_value(
        "borg_last_backup_timestamp", labels={"repository": "/borg/backup-1"}
    )
    assert arrow.get(last_backup_timestamp)
