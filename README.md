# Borgmatic Exporter

![Super-Linter](https://github.com/maxim-mityutko/borgmatic-exporter/actions/workflows/build.yml/badge.svg)
![GitHub last commit (branch)](https://img.shields.io/github/last-commit/maxim-mityutko/borgmatic-exporter/master)
![Static Badge](https://img.shields.io/badge/Borgmatic%20Image-v2.2.0-green)

**Borgmatic Exporter** seamlessly integrates Prometheus metrics and Borgmatic. This project is based on
the [borg-exporter](https://github.com/danihodovic/borg-exporter) by [@danihodovic](https://github.com/danihodovic),
however it introduces a few changes:

- extra metrics
- native integration with the official Borgmatic docker image
- results caching

## Metrics

| Name                                          | Type  |
|-----------------------------------------------|-------|
| borg_total_backups                            | Gauge |
| borg_total_chunks                             | Gauge |
| borg_total_size                               | Gauge |
| borg_total_compressed_size                    | Gauge |
| borg_total_deduplicated_size                  | Gauge |
| borg_total_deduplicated_compressed_size       | Gauge |
| borg_last_backup_timestamp                    | Gauge |
| borg_last_backup_duration                     | Gauge |
| borg_last_backup_files                        | Gauge |
| borg_last_backup_deduplicated_compressed_size | Gauge |
| borg_last_backup_compressed_size              | Gauge |
| borg_last_backup_size                         | Gauge |

## Installation

### Docker

Recommended way of using **Borgmatic Exporter** is through Docker. The image
is based on the official [docker-borgmatic](https://github.com/borgmatic-collective/docker-borgmatic)
image, and it seamlessly integrates Prometheus metrics into the distribution by running both Borgmatic
entrypoint and exporter server in parallel. All images are available
[here](https://github.com/maxim-mityutko/borgmatic-exporter/pkgs/container/borgmatic-exporter).

```shell
docker pull ghcr.io/maxim-mityutko/borgmatic-exporter:latest
```

1. Configure Borgmatic: <https://github.com/borgmatic-collective/docker-borgmatic/blob/master/README.md>
2. Configure Borgmatic Exporter:

    **Borgmatic Exporter** supports the following environment variables for customization:

    | Name                             | Description                                                                | Default                     |
    |----------------------------------|----------------------------------------------------------------------------|-----------------------------|
    | BORGMATIC_CONFIG                 | One or multiple references to Borgmatic configuration files                | /etc/borgmatic.d/config.yml |
    | BORGMATIC_EXPORTER_HOST          | Host for the metrics server                                                | 0.0.0.0                     |
    | BORGMATIC_EXPORTER_PORT          | Port for the metrics server                                                | 9996                        |
    | BORGMATIC_EXPORTER_TIME          | Display time each Borgmatic call takes                                     | false                       |
    | BORGMATIC_EXPORTER_CACHE_TIMEOUT | Cache the response of the metrics endpoint for the given number of seconds | 600                         |

#### Notes

- Use colon (`:`) if multiple configs should be provided through the environment variable `BORGMATIC_CONFIG`,
    e.g. `/etc/borgmatic/config_1.yml:/etc/borgmatic/config_2.yml`
- If **keyfiles** need to be provided to Borgmatic Exporter, mount the volume containing the keys to both `/root/.config/borg`
    and `/tmp/borgmatic-exporter-cache/.config/borg` (ref: [#43](https://github.com/maxim-mityutko/borgmatic-exporter/issues/43))
- Set `BORGMATIC_EXPORTER_CACHE_TIMEOUT` environment variable to 0 to disable metrics caching

### Local

Install and configure [borgmatic](https://github.com/witten/borgmatic) by following the instructions in the
official repository, then install **Borgmatic Exporter**

```shell
git clone https://github.com/maxim-mityutko/borgmatic-exporter.git
pip install -Ur requirements.txt
python3 cli.py run -c <path-to-your-borgmatic-config-yml>
```

## Observability and Monitoring

### Grafana

- Global view
![dashboard.png](observability%2Fdashboard-global.png)

- Repository details view
![dashboard.png](observability%2Fdashboard-details.png)
Dashboard is available in the [repo](/observability/grafana-dashboard.json) or on
[Grafana's Dashboard Library](https://grafana.com/grafana/dashboards/20334).

### Alerts

Alerting rules can be found [here](observability%2Fprometheus-alert.yaml). By default alert will
be triggered if there is no backup for repository within 25 hours.

## Development

### Local Environment

- Install [Poetry](https://python-poetry.org)
- Use provided `Makefile` to setup environment: `make dev`
- Run tests: `make test`

### Docker

- Build and run

    ```shell
    docker build -t borgmatic:tag .
    docker run --name borgmatic borgmatic:tag
    ```

- Rename or remove existing container, if the same name is already in use

    ```shell
    docker container ls -a
    docker container rm container-id
    ```

- Exec into the container and create config

    ```shell
    docker exec -it borgmatic /bin/sh
    
    borgmatic config generate
    
    # The default config will have entries for both remote and local repo
    # Remote repo config should be commented before proceeding
    vi /etc/borgmatic/config.yaml
    
    borgmatic init --encryption repokey
    ```

- Misc

    ```shell
    # Output repo info in JSON format
    borgmatic info --json --last 1
    # Create backup
    borgmatic create
    # Run exporter
    python3 cli.py run --config /etc/borgmatic/config.yaml
    ```

### Integration tests

The fast tests remain available with `make test` (or `poetry run pytest`).
They do not need Docker, Borg, or borgmatic. Integration tests are selected
explicitly and fail, rather than skip, if a required tool is missing.

#### Run in CI without a local Docker environment

Open **Actions → Build Image → Run workflow**, choose your branch and a
`borgmatic-image-version` (defaults to `latest`), and leave
**publish-image** unchecked. Manual runs test without publishing by default.
GitHub only offers this manual workflow once it exists on the default branch;
pull requests run it automatically.

CI runs the real container suite on `linux/amd64` and `linux/arm64`
(the latter via QEMU). It also runs on pushes to main/master, release tags, and
weekly against the latest upstream image. Check the **Integration (amd64)** and
**Integration (arm64)** jobs. Each uploads an **integration-results-…** artifact
with JUnit results, command logs, service logs, image details, and tool versions.

The base image is resolved to a digest once for both builds. Release tags, or
manual runs with **publish-image** checked, publish only after unit tests, lint,
and both integration jobs pass. Publication uses the saved, tested images without
rebuilding; manual publication uses the `dev` tag. Pull requests, branch
pushes, and scheduled runs never publish.

#### Run locally without Docker

For the real backup/metrics tests, install Borg **1.x** and
[borgmatic](https://torsion.org/borgmatic/how-to/set-up-backups/) on your PATH,
alongside the project's Poetry development environment:

```shell
borg --version
borgmatic --version
make integration-test INTEGRATION_BACKEND=native
```

Native mode starts the exporter as a subprocess using the Poetry interpreter,
backs up temporary files to temporary repositories, and scrapes its HTTP endpoint.
It isolates Borg keys, caches, configuration, and state from your normal setup.
It covers the Borg/borgmatic/exporter contract; Docker packaging and S6 startup
are additionally checked by the Docker suite in CI. Native mode requires Linux
or macOS.

#### Run locally with Docker

```shell
# Build the production Dockerfile and run the full container suite.
make integration-test

# Select the same base image version as a CI run.
make integration-test BORGMATIC_IMAGE_VERSION=2.2.0

# Test an existing image without rebuilding.
poetry run pytest -m integration --integration-backend=docker \
  --integration-image=borgmatic-exporter:integration tests/integration
```

The Docker suite requires a reachable local Docker daemon and uses the image's
normal `/init` entrypoint. Test tools run on the host; no test dependencies
are installed into the image. Containers, volumes, repository names, and HTTP
ports are isolated for each test, and container resources are removed on teardown.
No remote backup service or production credentials are required.

The suite verifies empty repositories, all 12 metric values against independent
Borg JSON output, new-backup refresh, multiple repositories and configuration
files/directories, unencrypted/repokey/keyfile repositories, cache expiry,
repository failure/recovery, and scraping while a repository lock is held.
The cache test intentionally takes at least one minute.

Local diagnostics are written to `.integration-artifacts/` (gitignored).
Use `--integration-artifacts=/another/path` with pytest to change that location.
