ARG BORGMATIC_IMAGE_VERSION="latest"
ARG BORGMATIC_IMAGE="ghcr.io/borgmatic-collective/borgmatic:${BORGMATIC_IMAGE_VERSION}"
FROM ${BORGMATIC_IMAGE}
ARG BORGMATIC_IMAGE
ARG BORGMATIC_IMAGE_VERSION

LABEL org.opencontainers.image.source="https://github.com/maxim-mityutko/borgmatic-exporter"
LABEL org.opencontainers.image.base.name="${BORGMATIC_IMAGE}"
LABEL org.opencontainers.image.title="Borgmatic Exporter"
LABEL org.opencontainers.image.description="Borgmatic backup automation with Prometheus metrics for repository size, deduplication, archive counts and latest backup details. Supports multiple repositories and configurable metrics caching. Based on the official Borgmatic image version ${BORGMATIC_IMAGE_VERSION}."


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
