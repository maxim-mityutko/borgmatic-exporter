import json
import os
import time
from threading import Thread
from pathlib import Path

import pytest
import requests
from prometheus_client import CollectorRegistry

from src.http_server import start_http_server

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture(scope="function")
def mock_run_command(mocker):
    with open(f"{PROJECT_ROOT}/data/repo-info.json") as j:
        ri = json.load(j)

    yield mocker.patch("src.metrics.run_command", return_value=ri)


@pytest.fixture(scope="function")
def server():
    registry = CollectorRegistry()
    host = "0.0.0.0"
    port = 9996
    cache_timeout = 300
    borg_home = Path("/tmp/borgmatic-exporter-cache")
    Thread(
        target=start_http_server,
        args=("/conf/foo.yml", registry, host, port, cache_timeout, borg_home),
        daemon=True,
    ).start()

    time.sleep(0.5)


def test_metrics_endpoint(server, mock_run_command):
    http = requests.Session()
    response = http.get("http://localhost:9996/metrics")
    assert "borg_total_backups" in response.text
    assert (
        'borg_total_deduplicated_size{repository="/borg/backup-2"} 2.1296544339e+010'
        in response.text
    )
