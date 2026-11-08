"""Exercise Borg, borgmatic, and the exporter in the unmodified Docker image."""

# pylint: disable=too-many-instance-attributes
import contextlib
import json
import subprocess
import time
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from prometheus_client.parser import text_string_to_metric_families

COMMAND_TIMEOUT = 180


def wait_until(predicate, description, timeout=60):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.2)
    raise AssertionError(f"Timed out waiting for {description}")


class ExporterPair:
    def __init__(self, image, workspace, artifacts):
        self.image = image
        self.workspace = workspace
        self.artifacts = artifacts
        self.name = f"borgmatic-integration-{uuid.uuid4().hex}"
        self.root = "/integration"
        self.config_dir = "/etc/borgmatic.d"
        self.repositories = []
        self.configs = []
        self.environment = {}
        self.base_url = ""
        self.artifacts.mkdir(parents=True, exist_ok=True)

    def host_command(self, command, *, check=True, timeout=COMMAND_TIMEOUT):
        with (self.artifacts / "commands.log").open("a", encoding="utf-8") as log:
            log.write(f"$ {command!r}\n")
            try:
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                log.write(f"Command timed out after {timeout}s\n")
                raise
            log.write(result.stdout + result.stderr)
        if check and result.returncode:
            raise AssertionError(
                f"Command failed ({result.returncode}): {command!r}\n"
                f"{result.stdout}\n{result.stderr}"
            )
        return result

    def command(self, *args, **kwargs):
        return self.host_command(["docker", "exec", self.name, *args], **kwargs)

    def python(self, script, *args):
        return self.command("python3", "-c", script, *args)

    def write(self, path, content):
        self.python(
            "from pathlib import Path; import sys; "
            "Path(sys.argv[1]).write_text(sys.argv[2], encoding='utf-8')",
            path,
            content,
        )

    def rename(self, source, destination):
        self.python(
            "from pathlib import Path; import sys; "
            "Path(sys.argv[1]).rename(sys.argv[2])",
            source,
            destination,
        )

    def configure(self, config_mode, repository_count):
        self.repositories = [
            f"{self.root}/repo-{index}" for index in range(repository_count)
        ]
        config_groups = (
            [[repo] for repo in self.repositories]
            if config_mode in ("multiple", "directory")
            else [self.repositories]
        )
        configs_dir = self.workspace / "configs"
        configs_dir.mkdir()
        source = self.workspace / "source"
        source.mkdir()
        (source / "first.txt").write_text("first backup\n" * 200, encoding="utf-8")
        for index, repositories in enumerate(config_groups):
            filename = "config.yml" if index == 0 else f"config-{index}.yml"
            self.configs.append(f"{self.config_dir}/{filename}")
            config = {
                "source_directories": [f"{self.root}/source"],
                "repositories": [{"path": repo} for repo in repositories],
                "archive_name_format": "integration-{now:%Y-%m-%dT%H:%M:%S.%f}",
                "compression": "none",
                "store_config_files": False,
                "user_runtime_directory": f"{self.root}/runtime",
                "user_state_directory": f"{self.root}/state",
            }
            # JSON is valid YAML, so the harness needs no YAML serializer.
            (configs_dir / filename).write_text(json.dumps(config), encoding="utf-8")
        return self.config_dir if config_mode == "directory" else ":".join(self.configs)

    def start(self, config_mode="default", repository_count=1, cache_timeout=0):
        config = self.configure(config_mode, repository_count)
        self.environment = {
            "TZ": "UTC",
            "BORG_PASSPHRASE": "integration-test-passphrase",
            "BORG_UNKNOWN_UNENCRYPTED_REPO_ACCESS_IS_OK": "yes",
            "BORGMATIC_EXPORTER_HOST": "0.0.0.0",
            "BORGMATIC_EXPORTER_CACHE_TIMEOUT": str(cache_timeout),
        }
        if config_mode != "default":
            self.environment["BORGMATIC_CONFIG"] = config
        self.start_container()
        versions = [
            self.command("borg", "--version").stdout,
            self.command("borgmatic", "--version").stdout,
            self.python("import sys; print(sys.version)").stdout,
        ]
        (self.artifacts / "versions.txt").write_text(
            "\n".join(versions), encoding="utf-8"
        )
        wait_until(self.ready, "exporter HTTP startup", timeout=90)

    def start_container(self):
        self.environment["CRON"] = "false"
        # Share keyfiles at both documented locations, while keeping caches separate.
        self.host_command(["docker", "volume", "create", self.name])
        command = [
            "docker",
            "create",
            "--name",
            self.name,
            "--publish",
            "127.0.0.1::9996",
            "--mount",
            "type=volume,dst=/etc/borgmatic.d,volume-nocopy",
            "--mount",
            f"type=volume,src={self.name},dst=/root/.config/borg",
            "--mount",
            f"type=volume,src={self.name},dst=/tmp/borgmatic-exporter-cache/.config/borg",
        ]
        for key, value in self.environment.items():
            command.extend(["--env", f"{key}={value}"])
        command.append(self.image)
        self.host_command(command)
        self.host_command(
            ["docker", "cp", f"{self.workspace}/.", f"{self.name}:{self.root}"]
        )
        self.host_command(
            [
                "docker",
                "cp",
                f"{self.workspace}/configs/.",
                f"{self.name}:{self.config_dir}",
            ]
        )
        self.host_command(["docker", "start", self.name])
        address = self.host_command(
            ["docker", "port", self.name, "9996/tcp"]
        ).stdout.strip()
        self.base_url = f"http://{address}"

    def get(self, path):
        try:
            with urlopen(f"{self.base_url}{path}", timeout=30) as response:
                return response.status, response.read().decode(), response.headers
        except HTTPError as error:
            return error.code, error.read().decode(), error.headers

    def ready(self):
        try:
            return self.get("/")[0] == 200
        except (URLError, TimeoutError):
            return False

    def scrape(self):
        status, body, headers = self.get("/metrics")
        assert status == 200, f"Metrics returned HTTP {status}: {body}"
        assert "text/plain" in headers["Content-Type"]
        samples = {}
        for family in text_string_to_metric_families(body):
            for sample in family.samples:
                key = (sample.name, sample.labels["repository"])
                assert key not in samples, f"Duplicate metric: {key}"
                samples[key] = sample.value
        assert samples, "Exporter returned no repository metrics"
        return samples

    def borgmatic(self, *args):
        config_args = [part for config in self.configs for part in ("-c", config)]
        return self.command("borgmatic", *config_args, "--verbosity", "-1", *args)

    def initialize(self, encryption="none"):
        self.borgmatic("repo-create", "--encryption", encryption)

    def backup(self, repository=None):
        args = ("--repository", repository) if repository else ()
        self.borgmatic("create", *args)

    def borg_json(self, action, repository, *args):
        # Query each repository directly: do not reuse the exporter's parser or
        # its multi-repository command construction as the expected-value oracle.
        return json.loads(
            self.command("borg", action, "--json", *args, repository).stdout
        )

    @contextlib.contextmanager
    def locked_repository(self, repository):
        ready = f"{self.root}/lock-ready"
        release = f"{self.root}/lock-release"
        script = (
            "from pathlib import Path; import time, sys; "
            "Path(sys.argv[1]).touch(); "
            "deadline = time.monotonic() + 120\n"
            "while not Path(sys.argv[2]).exists() and time.monotonic() < deadline:\n"
            " time.sleep(0.1)\n"
            "assert Path(sys.argv[2]).exists(), 'Lock release timed out'"
        )
        command = [
            "docker",
            "exec",
            self.name,
            "borg",
            "with-lock",
            repository,
            "python3",
            "-c",
            script,
            ready,
            release,
        ]
        with (self.artifacts / "lock.log").open("w", encoding="utf-8") as log:
            process = subprocess.Popen(
                command,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            try:
                wait_until(
                    lambda: self.command("test", "-f", ready, check=False).returncode
                    == 0,
                    "repository lock",
                    timeout=30,
                )
                yield
                self.write(release, "release")
                assert process.wait(timeout=30) == 0
            finally:
                if process.poll() is None:
                    try:
                        self.write(release, "release")
                    finally:
                        self.stop_process(process)

    @staticmethod
    def stop_process(process):
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)

    def close(self):
        try:
            result = self.host_command(["docker", "logs", self.name], check=False)
            (self.artifacts / "container.log").write_text(
                result.stdout + result.stderr, encoding="utf-8"
            )
            result = self.host_command(["docker", "inspect", self.name], check=False)
            (self.artifacts / "container.json").write_text(
                result.stdout, encoding="utf-8"
            )
        finally:
            self.host_command(
                ["docker", "rm", "--force", "--volumes", self.name], check=False
            )
            self.host_command(["docker", "volume", "rm", self.name], check=False)
