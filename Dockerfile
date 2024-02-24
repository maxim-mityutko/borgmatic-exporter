FROM b3vis/borgmatic:1.8.8

LABEL org.opencontainers.image.source="https://github.com/maxim-mityutko/borgmatic-exporter"
LABEL org.opencontainers.image.base.name="borgmatic:1.8.5"
LABEL org.opencontainers.image.title="Borgmatic Exporter"
LABEL org.opencontainers.image.description="Official Borgmatic image bundled with the Prometheus exporter"


RUN apk add --update --no-cache git supervisor\
    && rm -rf /var/cache/apk/* /.cache

RUN mkdir -p /var/log/supervisor
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

COPY ./src exporter/src
COPY ./cli.py exporter/
COPY ./requirements.txt exporter/
COPY ./supervisord.conf exporter/

# Won't be installing `poetry` into the image to reduce image size, instead `requirements.txt` will be used.
# Update requirements.txt manually with:
#       poetry export -f requirements.txt --output requirements.txt --without dev --without-hashes
# Or setup a pre-commit hook:
#       https://python-poetry.org/docs/pre-commit-hooks/#poetry-export

WORKDIR /exporter/

RUN python3 -m pip install --no-cache -Ur requirements.txt
RUN chmod 755 /exporter/cli.py

ENTRYPOINT ["/usr/bin/supervisord"]