import json
import os
import time
from threading import Thread

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
    port = 9996
    Thread(
        target=start_http_server,
        args=("/conf/foo.yml", registry, port),
        daemon=True,
    ).start()

    time.sleep(0.5)


def test_metrics_endpoint(server, mock_run_command):
    http = requests.Session()
    response = http.get("http://localhost:9996/metrics")
    assert "borg_total_backups" in response.text
    assert (
        'borg_unique_size{repository="/borg/backup-2"} 2.1296544339e+010'
        in response.text
    )
