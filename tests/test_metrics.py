import json
import os

import pytest
from prometheus_client import CollectorRegistry

from src import metrics

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


class TestMetrics:
    @pytest.fixture(scope="function")
    def registry(self):
        registry = CollectorRegistry(auto_describe=True)
        yield registry

    @pytest.fixture(scope="function")
    def collect(self, mocker, registry):
        with open(f"{PROJECT_ROOT}/data/repo-info.json") as j:
            ri = json.load(j)

        mocker.patch("src.metrics.run_command", return_value=ri)

        metrics.create_metrics(registry=registry)
        metrics.collect(
            borgmatic_configs=["/conf/foo.yaml", "/conf/bar.yaml", "/conf/baz.yaml"],
            registry=registry,
        )
        yield registry

    def test_run_command(self):
        result = metrics.run_command(command='echo {"foo": "bar"}')
        assert result == {"foo": "bar"}

    def test_registry(self, registry):
        result = metrics.create_metrics(registry=registry)._names_to_collectors
        assert "borg_total_backups" in result
        assert "borg_total_chunks" in result
        assert "borg_total_compressed_size" in result
        assert "borg_total_size" in result
        assert "borg_total_deduplicated_compressed_size" in result
        assert "borg_total_deduplicated_size" in result
        assert "borg_last_backup_timestamp" in result

    @pytest.mark.parametrize(
        "metric, repo, expect",
        [
            ("borg_total_backups", "/borg/backup-1", 2.0),
            ("borg_total_backups", "/borg/backup-3", 0.0),
            ("borg_total_chunks", "/borg/backup-1", 3505.0),
            ("borg_total_compressed_size", "/borg/backup-1", 3965903861.0),
            ("borg_total_size", "/borg/backup-1", 8446787072.0),
            ("borg_total_deduplicated_compressed_size", "/borg/backup-1", 537932015.0),
            ("borg_total_deduplicated_size", "/borg/backup-1", 1296544339.0),
            ("borg_total_deduplicated_size", "/borg/backup-2", 21296544339.0),
            ("borg_last_backup_timestamp", "/borg/backup-1", 1704790914.0),
        ],
    )
    def test_individual_metrics(self, collect, metric, repo, expect):
        registry = collect
        actual = registry.get_sample_value(name=metric, labels={"repository": repo})
        assert actual == expect
