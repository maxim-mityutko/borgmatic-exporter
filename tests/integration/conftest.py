import shutil
import subprocess
from pathlib import Path

import pytest

from tests.integration.harness import ExporterPair


@pytest.fixture(scope="session")
def integration_settings(request):
    backend = request.config.getoption("--integration-backend")
    required = ("docker",) if backend == "docker" else ("borg", "borgmatic")
    missing = [command for command in required if shutil.which(command) is None]
    if missing:
        pytest.fail(
            f"Integration backend {backend!r} requires: {', '.join(missing)}. "
            "Install the prerequisites or run the GitHub Actions workflow. "
            "Use 'make test' for tests without these dependencies.",
            pytrace=False,
        )
    image = request.config.getoption("--integration-image")
    if backend == "docker":
        for command in (["docker", "info"], ["docker", "image", "inspect", image]):
            try:
                result = subprocess.run(
                    command, capture_output=True, text=True, timeout=30, check=False
                )
            except subprocess.TimeoutExpired:
                pytest.fail(
                    f"Docker prerequisite timed out: {command!r}", pytrace=False
                )
            if result.returncode:
                pytest.fail(
                    f"Docker prerequisite failed: {command!r}\n{result.stderr}\n"
                    "Start Docker and run 'make integration-test' to build the image.",
                    pytrace=False,
                )
    return backend, image


@pytest.fixture
def pair_factory(request, tmp_path, integration_settings):
    pairs = []

    def create(**kwargs):
        backend, image = integration_settings
        workspace = tmp_path / f"pair-{len(pairs)}"
        workspace.mkdir()
        artifacts = (
            Path(request.config.getoption("--integration-artifacts"))
            / request.node.name
            / str(len(pairs))
        ).resolve()
        pair = ExporterPair(backend, image, workspace, artifacts)
        pairs.append(pair)
        pair.start(**kwargs)
        return pair

    yield create
    for pair in reversed(pairs):
        pair.close()
