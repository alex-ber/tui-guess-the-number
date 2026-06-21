FROM alexberkovich/ubuntu2404-snapshot:2025-06-16



#[HARDWARE_CONFIG]: Deterministic execution and compilation flags
# Consolidated environment variables to reduce layer allocation overhead.
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    LANG=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_CACHE_DIR=/tmp/.uv-cache \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_INSTALL_DIR=/opt/python

WORKDIR /app

#[HARDWARE_BRIDGE]: Injecting UV Compiler (AOT Dependency Graph Resolver)
COPY --from=ghcr.io/astral-sh/uv@sha256:ff07b86af50d4d9391d9daf4ff89ce427bc544f9aae87057e69a1cc0aa369946 /uv /uvx /bin/

#[RUNTIME_ENVIRONMENT]: Deterministic APT Projection & Root Python Allocation
RUN set -ex && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    nano \
    && rm -rf /var/lib/apt/lists/* \
    && echo 'set syntax "none"' >> /etc/nanorc && \
    uv python install 3.14.6

#[DEPENDENCY_INJECTION]: Top-Down Directed Acyclic Graph Mount
COPY pyproject.toml uv.lock ./

#[POINTER_ALLOCATION]: Synthetic Mock-Node Cache Strategy
# Bypasses hatchling early parse exception, isolating dependency layer from source layer jitter.
RUN set -ex && \
    mkdir -p src/tui-guess-the-number && \
    echo '__version__ = "0.0.1"' > src/tui-guess-the-number/__init__.py && \
    uv sync --no-install-project

#[AST_COPY]: Mount Root Logic
COPY src/ src/

#[PROJECT_INJECTION]: Finalize Symbol Table Linkage
RUN set -ex && \
    uv sync && \
    chmod -R 777 /app/.venv && \
    chmod -R 755 /opt/python && \
    chmod -R 777 /tmp/.uv-cache && \
    mkdir -p /app/logs && \
    chmod -R 777 /app/logs


#[ENTRYPOINT]: Hardware Transition (Main Thread Execution)
# Use ENTRYPOINT for the fixed executable part
ENTRYPOINT ["uv", "run", "python", "-m", "src.tui-guess-the-number.guess"]

# Use CMD for default arguments (empty by default)
CMD ["--min", "1", "--max", "1023", "--player-a", "human", "--player-b", "human"]

#CMD ["uv", "run", "python", "-m", "src.tui-guess-the-number.guess"]
#CMD ["sleep", "infinity"]


#mise prune
#mise install
# ---[STATELESS BIRUR DAEMON] ---
# To regenerate uv.lock WITHOUT installing uv on the Host OS, run this ephemeral hypervisor:
# docker run --rm -v "$(pwd):/app" -w /app ghcr.io/astral-sh/uv:python3.14-bookworm-slim uv lock

#docker build --no-cache --progress=plain -t tui-guess-the-number-i .
#docker run -it -p 8080:8080 -v "$(pwd)/.secrets:/app/.secrets" tui-guess-the-number-i
# The --entrypoint /bin/bash flag overrides the default script execution.
# You get a Linux command line INSIDE the container.
#docker run -it -p 8080:8080 --entrypoint /bin/bash -v "$(pwd)/.secrets:/app/.secrets" tui-guess-the-number-i

# ---[PyPI PUBLISHING PIPELINE] ---
# uv build
# Allocate token in RAM (Replace YOUR_TOKEN):
# export UV_PUBLISH_TOKEN="pypi-YOUR_TOKEN"
# Transmit artifacts to WAN (PyPI):
# uv publish 


#sudo -E env PATH="$PATH" uv
#uv cache dir #~/.cache/uv
#uv cache clean #completely wipe out cache
#uv cache prune #outdated
#uv cache clean numpy #If you suspect a specific package is corrupted or you wa>
#uv sync
#uv run python -m src.the_number.guess




#docker tag tui-guess-the-number-i alexberkovich/tui-guess-the-number:0.0.1
#docker tag tui-guess-the-number-i alexberkovich/tui-guess-the-number:latest
#docker push alexberkovich/tui-guess-the-number:0.0.1
#docker push alexberkovich/tui-guess-the-number:latest


# Delete all containers
# docker rm -f $(docker ps -a -q)

# This command will only show the dangling images 
# (images that are not tagged or referenced by any container)
# docker images -f "dangling=true"

# Delete all dangling images
# docker image prune -f

# Delete all unused images
# docker image prune -a -f

# Delete all images
# docker rmi -f $(docker images -q)

# Delete all build cache
# docker builder prune --all
# Verify builder cache deleted
# docker builder du

# https://gallery.ecr.aws/lambda/python/
# docker volume ls
# docker volume ls -q > volumes-to-delete.txt
# Review volumes-to-delete.txt and delete only anonymous or never be used one.
# xargs -r docker volume rm < volumes-to-delete.txt
## docker system prune --all
# docker rm -f tui-guess-the-number
# docker rmi -f tui-guess-the-number-i

# docker build --no-cache . -t tui-guess-the-number-i
# docker build --no-cache --progress=plain . -t tui-guess-the-number-i

# docker run --rm -it tui-guess-the-number-i bash
# docker exec -it $(docker ps -q -n=1) bash

# sudo docker stats | sudo tee -a docker_stats.log
# sudo watch -n 15 "docker stats --no-stream | sudo tee -a docker_stats.log"
# RAM+SWAP memory
# watch -n 1 free -h




