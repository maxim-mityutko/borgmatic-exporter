# Borgmatic Exporter
[![Super-Linter](https://github.com/maxim-mityutko/borgmatic-exporter/actions/workflows/build.yml/badge.svg)](https://github.com/marketplace/actions/super-linter)

**Borgmatic Exporter** seamlessly integrates Prometheus metrics and Borgmatic. This project is based on
the [borg-exporter](https://github.com/danihodovic/borg-exporter) by [@danihodovic](https://github.com/danihodovic),
however it introduces a few changes:

- extra metrics
- native integration with the official Borgmatic docker image



## Metrics
| Name                       | Description                              | Type  |
|----------------------------|------------------------------------------|-------|
| borg_unique_size           | Uncompressed size of the Borg repository | Gauge |
| borg_total_size            | Total size of the Borg repository        | Gauge |
| borg_total_backups         | Total number of Borg backups             | Gauge |
| borg_last_backup_timestamp | Timestamp of the last Borg backup        | Gauge |

## Installation
### Docker
Recommended way of using **Borgmatic Exporter** is through Docker. The image 
is based on the official [docker-borgmatic](https://github.com/borgmatic-collective/docker-borgmatic)
image, and it seamlessly integrates Prometheus metrics into the distribution by running both Borgmatic 
entrypoint and exporter server in parallel.

Follow the instructions in the above-mentioned repository to set up Borgmatic. 

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
python3 cli.py run
```


# TODO UPDATE ME
![Dashboard](./images/borg_grafana_dashboard.png)

## Alerting rules

Alerting rules can be found [here](./borg-mixin/prometheus-alerts.yaml). By
default Prometheus sends an alert if a backup hasn't been issued in 24h5m.

## Grafana Dashboard

You can find the generated Grafana dashboard [here](./borg-mixin/dashboards_out/dashboard.json) and it can be imported directly into the Grafana UI.

It's also available in [Grafana's Dashboard Library](https://grafana.com/grafana/dashboards/14489).
