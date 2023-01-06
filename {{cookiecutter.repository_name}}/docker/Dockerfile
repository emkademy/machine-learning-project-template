FROM nvidia/cuda:11.6.1-cudnn8-runtime-ubuntu20.04

ARG USER_ID=1000
ARG DEV_MODE=0
ARG USER_NAME={{cookiecutter.project_name}}
ENV HOME=/home/$USER_NAME
ENV \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    TZ=Europe/Warsaw \
    VIRTUAL_ENV=$HOME/venv \
    PATH="/usr/local/gcloud/google-cloud-sdk/bin:$HOME/venv/bin:$PATH" \
    PYTHONPATH="/app:$PYTHONPATH" \
    BUILD_POETRY_LOCK="${HOME}/poetry.lock.build"

RUN apt-get -qq update \
    && apt-get -qq -y install vim gcc curl git build-essential libb64-dev software-properties-common llvm-10-dev \
    && ln -s /usr/bin/llvm-config-10 /usr/bin/llvm-config \
    && add-apt-repository ppa:deadsnakes/ppa -y \
    && apt-get update \
    && apt-get install python3.9 python3.9-distutils python3.9-venv python3.9-dev -y \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get -qq -y clean

RUN python3.9 -m ensurepip --upgrade

# Install gcloud and gsutils
RUN curl https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-396.0.0-linux-x86_64.tar.gz > /tmp/google-cloud-sdk.tar.gz
RUN mkdir -p /usr/local/gcloud \
    && tar -C /usr/local/gcloud -xf /tmp/google-cloud-sdk.tar.gz \
    && /usr/local/gcloud/google-cloud-sdk/install.sh --usage-reporting false --command-completion true --bash-completion true --path-update true --quiet

RUN addgroup --system --gid ${USER_ID} ${USER_NAME} \
    && useradd --system -m --no-log-init --home-dir ${HOME} --uid ${USER_ID} --gid ${USER_NAME} --groups ${USER_NAME} ${USER_NAME}

RUN chown -R $USER_NAME $HOME
RUN mkdir -p /app && chown $USER_NAME /app /tmp

RUN HOME=/tmp python3.9 -m pip install poetry==1.2.2

USER $USER_NAME

COPY pyproject.toml *.lock /app/
WORKDIR /app

RUN python3.9 -m venv $VIRTUAL_ENV \
    && pip install --upgrade pip setuptools \
    && if [ $DEV_MODE -eq 1 ]; then \
        poetry install && cp poetry.lock "${BUILD_POETRY_LOCK}"; \
    else \
        [ -f poetry.lock ] || { echo 'No poetry.lock found' ; exit 1; }; \
        poetry install --no-dev; \
    fi \
    && rm -rf $HOME/.cache/*

USER root
COPY ./docker/scripts/* /
RUN chown -R ${USER_NAME} /*.sh && chmod +x /*.sh
USER $USER_NAME

COPY . /app/
CMD ["/startup-script.sh"]
