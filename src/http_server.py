from flask import Blueprint, Flask, current_app, request
from flask_caching import Cache
from loguru import logger
from prometheus_client.exposition import choose_encoder
from waitress import serve

from src.metrics import collect, create_metrics

blueprint = Blueprint("borg_exporter", __name__)

cache_config = {
    "CACHE_TYPE": "SimpleCache",
}
cache = Cache(config=cache_config)


@blueprint.route("/")
def index():
    return """
        <!doctype html>
        <html lang="en">
          <head>
            <!-- Required meta tags -->
            <meta charset="utf-8">
            <title>borgmatic-exporter</title>
          </head>
          <body>
            <h1>Borgmatic Exporter</h1>
            <p><a href="/metrics">Metrics</a></p>
          </body>
        </html>
    """


@blueprint.route("/metrics")
@cache.cached()
def metrics():
    borgmatic_config = current_app.config["borgmatic_config"]
    registry = current_app.config["registry"]
    collect(borgmatic_config, registry)
    encoder, content_type = choose_encoder(request.headers.get("accept"))
    output = encoder(current_app.config["registry"])
    return output, 200, {"Content-Type": content_type}


def start_http_server(borgmatic_configs, registry, host, port, cache_timeout):
    if isinstance(borgmatic_configs, str):
        borgmatic_configs = (borgmatic_configs,)
    app = Flask(__name__)
    app.config["registry"] = create_metrics(registry)
    app.config["borgmatic_config"] = borgmatic_configs
    app.register_blueprint(blueprint)

    cache.init_app(app, config={"CACHE_DEFAULT_TIMEOUT": cache_timeout, **cache_config})

    logger.info("Started borgmatic-exporter at port='{}'", port)
    serve(app, host=host, port=port, _quiet=True)
