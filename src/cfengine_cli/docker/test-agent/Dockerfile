FROM debian:12-slim
ENV PATH="/root/.local/bin:${PATH}"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 pipx sudo procps

RUN pipx install cfengine

RUN cfengine install --clients localhost --edition community

RUN mkdir -p /var/cfengine/bin/ \
    && ln -sf "$(command -v python3)" /var/cfengine/bin/cfengine-selected-python
