# Task generation engine: SageMath + taskgen Python deps.
# The repository is bind-mounted at /work (see compose.yaml); taskgen is
# imported from there via PYTHONPATH, so code edits need no rebuild.
FROM sagemath/sagemath:latest

USER root
RUN apt-get update \
 && apt-get install -y --no-install-recommends git \
 && rm -rf /var/lib/apt/lists/*

COPY docker/taskgen/requirements.txt /tmp/requirements.txt
RUN sage -pip install --no-cache-dir -r /tmp/requirements.txt

# Allow running as an arbitrary host uid (compose passes `user:`).
ENV DOT_SAGE=/tmp/.sage \
    HOME=/tmp \
    PYTHONPATH=/work \
    PYTHONDONTWRITEBYTECODE=1 \
    GIT_CONFIG_COUNT=1 \
    GIT_CONFIG_KEY_0=safe.directory \
    GIT_CONFIG_VALUE_0=*

WORKDIR /work
ENTRYPOINT ["sage", "-python", "-m", "taskgen"]
