def pytest_addoption(parser):
    group = parser.getgroup("integration")
    group.addoption(
        "--integration-backend",
        choices=("docker", "native"),
        default="docker",
        help="Run the release image, or locally installed Borg and borgmatic.",
    )
    group.addoption(
        "--integration-image",
        default="borgmatic-exporter:integration",
        help="Existing Docker image to test; the suite does not rebuild it.",
    )
    group.addoption(
        "--integration-artifacts",
        default=".integration-artifacts",
        help="Directory for integration command, service, and version logs.",
    )
