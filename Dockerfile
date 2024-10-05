ARG BORGMATIC_IMAGE_VERSION="latest"
FROM ghcr.io/borgmatic-collective/borgmatic:1.8.13

LABEL org.opencontainers.image.source="https://github.com/maxim-mityutko/borgmatic-exporter"
LABEL org.opencontainers.image.base.name="borgmatic:$BORGMATIC_IMAGE_VERSION"
LABEL org.opencontainers.image.title="Borgmatic Exporter"
LABEL org.opencontainers.image.description="Official Borgmatic image bundled with the Prometheus exporter"


COPY ./src exporter/src
COPY ./cli.py exporter/
COPY ./requirements.txt exporter/

# Copy S6-overlay configs
COPY --chmod=744 --link root/ /

# Won't be installing `poetry` into the image to reduce image size, instead `requirements.txt` will be used.
# Update requirements.txt manually with:
#       poetry export -f requirements.txt --output requirements.txt --without dev --without-hashes
# Or setup a pre-commit hook:
#       https://python-poetry.org/docs/pre-commit-hooks/#poetry-export

WORKDIR /exporter/

RUN python3 -m pip install --no-cache -Ur requirements.txt
RUN chmod 755 /exporter/cli.py

ENTRYPOINT ["/init"]
