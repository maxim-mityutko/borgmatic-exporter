# Borgmatic Exporter
![Super-Linter](https://github.com/maxim-mityutko/borgmatic-exporter/actions/workflows/build.yml/badge.svg)
![GitHub last commit (branch)](https://img.shields.io/github/last-commit/maxim-mityutko/borgmatic-exporter/master)
![Static Badge](https://img.shields.io/badge/Borgmatic%20Image-v1.8.5-blue)


**Borgmatic Exporter** seamlessly integrates Prometheus metrics and Borgmatic. This project is based on
the [borg-exporter](https://github.com/danihodovic/borg-exporter) by [@danihodovic](https://github.com/danihodovic),
however it introduces a few changes:

- extra metrics
- native integration with the official Borgmatic docker image

## Metrics
| Name                                    | Type  |
|-----------------------------------------|-------|
| borg_total_backups                      | Gauge |
| borg_total_chunks                       | Gauge |
| borg_total_size                         | Gauge |
| borg_total_compressed_size              | Gauge |
| borg_total_deduplicated_size            | Gauge |
| borg_total_deduplicated_compressed_size | Gauge |
| borg_last_backup_timestamp              | Gauge |

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

1. Configure Borgmatic: https://github.com/borgmatic-collective/docker-borgmatic/blob/master/README.md
2. Configure Borgmatic Exporter:

    **Borgmatic Exporter** supports the following environment variables for customization:

    | Name                    | Description                                                 | Default                     |
    |-------------------------|-------------------------------------------------------------|-----------------------------|
    | BORGMATIC_CONFIG        | One or multiple references to Borgmatic configuration files | /etc/borgmatic.d/config.yml |
    | BORGMATIC_EXPORTER_PORT | Port for the metrics server                                 | 9996                        |
    | BORGMATIC_EXPORTER_TIME | Display time each Borgmatic call takes                      | false                       |

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
![dashboard.png](observability%2Fdashboard.png)
Dashboard is available in the [repo](/observability/grafana-dashboard.json) or on 
[Grafana's Dashboard Library](https://grafana.com/grafana/dashboards/20334).

### Alerts
Alerting rules can be found [here](observability%2Fprometheus-alert.yaml). By default alert will
be triggered if there is no backup for repository within 25 hours.

