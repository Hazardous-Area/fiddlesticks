ARG UBUNTU_TAG=26.04

FROM ubuntu:${UBUNTU_TAG}


ENV DEBIAN_FRONTEND=noninteractive

ARG INSTALL_7Z=false
ARG INSTALL_VERACRYPT=false
ARG TEST_ENV=false

RUN apt-get update && apt-get install -y \
    python3-venv \
    python3-pip \
    python-is-python3

RUN if [ "$INSTALL_7Z" != "false" ]; then \
        apt-get update && apt-get install -y 7zip; \
    fi

# Git is needed to make uses: actions/checkout work inside a
# Docker container e.g. when running the tests in Github Actions. 
RUN if [ "$TEST_ENV" != "false" ]; then \
        apt-get update && apt-get install -y git; \
    fi

RUN if [ "$INSTALL_VERACRYPT" != "false" ]; then \
        apt-get update && apt-get install -y wget && \
        wget http://archive.ubuntu.com/ubuntu/pool/main/f/fuse3/libfuse3-4_3.18.2-1_amd64.deb && \
        dpkg -i libfuse3-4_3.18.2-1_amd64.deb || apt-get install -f -y && \
        wget https://github.com/veracrypt/VeraCrypt/releases/download/VeraCrypt_1.26.29/veracrypt-console-1.26.29-Ubuntu-26.04-amd64.deb && \
        apt-get install -y software-properties-common && \
        add-apt-repository universe && \
        apt-get update && \
        apt-get install -y fuse3 libfuse3-dev && \
        apt-get install -y ./veracrypt-console-1.26.29-Ubuntu-26.04-amd64.deb && \
        rm *.deb; \
    fi

# Mandatory steps
WORKDIR /fiddlesticks
RUN python3 -m venv .venv

RUN .venv/bin/pip install --upgrade pip
# Only pyproject.toml is needed to install test dependency group
COPY ./LICENSE .
COPY ./pyproject.toml .
COPY ./README.md .

RUN if [ "$TEST_ENV" != "false" ]; then \
        .venv/bin/pip install --group=test && \
        # Install all deps of code under test now 
        # so they are cached in this Docker layer
        .venv/bin/pip install -e .[all] --only-deps; \
    fi