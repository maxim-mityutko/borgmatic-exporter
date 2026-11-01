import shutil
import subprocess
from pathlib import Path

import pytest

from tests.integration.harness import ExporterPair


@pytest.fixture(scope="session")
def integration_image(request):
    if shutil.which("docker") is None:
        pytest.fail(
            "Integration tests require Docker. Install Docker or run the "
            "GitHub Actions workflow. Use 'make test' for tests without Docker.",
            pytrace=False,
        )
    image = request.config.getoption("--integration-image")
    for command in (["docker", "info"], ["docker", "image", "inspect", image]):
        try:
            result = subprocess.run(
                command, capture_output=True, text=True, timeout=30, check=False
            )
        except subprocess.TimeoutExpired:
            pytest.fail(f"Docker prerequisite timed out: {command!r}", pytrace=False)
        if result.returncode:
            pytest.fail(
                f"Docker prerequisite failed: {command!r}\n{result.stderr}\n"
                "Start Docker and run 'make integration-test' to build the image.",
                pytrace=False,
            )
    return image


@pytest.fixture
def pair_factory(request, tmp_path, integration_image):
    pairs = []

    def create(**kwargs):
        workspace = tmp_path / f"pair-{len(pairs)}"
        workspace.mkdir()
        artifacts = (
            Path(request.config.getoption("--integration-artifacts"))
            / request.node.name
            / str(len(pairs))
        ).resolve()
        pair = ExporterPair(integration_image, workspace, artifacts)
        pairs.append(pair)
        pair.start(**kwargs)
        return pair

    yield create
    for pair in reversed(pairs):
        pair.close()
