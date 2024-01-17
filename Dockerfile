FROM b3vis/borgmatic:latest
RUN apk add --update --no-cache git supervisor\
    && rm -rf /var/cache/apk/* /.cache

RUN mkdir -p /var/log/supervisor
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

COPY . exporter

# Won't be installing `poetry` into the image to reduce image size, instead `requirements.txt` will be used.
# Update requirements.txt manually with:
#       poetry export -f requirements.txt --output requirements.txt --without dev --without-hashes
# Or setup a pre-commit hook:
#       https://python-poetry.org/docs/pre-commit-hooks/#poetry-export

WORKDIR /exporter/

RUN python3 -m pip install --no-cache -Ur requirements.txt
RUN chmod 755 /exporter/cli.py

# TODO: add to usage manual
# ENV BORGMATIC_CONFIG="/exporter/config.yml"
# ENV BORGMATIC_EXPORTER_PORT="1234"

ENTRYPOINT ["/usr/bin/supervisord"]