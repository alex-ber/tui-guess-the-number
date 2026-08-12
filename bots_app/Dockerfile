FROM alexberkovich/ubuntu2404-snapshot:2026-08-06



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
#https://github.com/astral-sh/uv/pkgs/container/uv/1073952945?tag=0.11.33-python3.12-trixie
COPY --from=ghcr.io/astral-sh/uv:0.11.33@sha256:77280f2f771df71f90786c314fe1bbc1e023feac652969bbf139c280babf2eb7 /uv /uvx /bin/

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
    mkdir -p src/tui-guess-the-number-bots && \
    echo '__version__ = "0.0.1"' > src/tui-guess-the-number-bots/__init__.py && \
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


# #It is the command that will start and run the FastAPI application container
CMD ["uv", "run", "python", "-m", "src.tui-guess-the-number-bots.main"]
#CMD ["sleep", "infinity"]



#mise prune
#mise install

#docker build --no-cache --progress=plain -t tui-guess-the-number-bots-i .
#docker run -it tui-guess-the-number--bots-i
# The --entrypoint /bin/bash flag overrides the default script execution.
# You get a Linux command line INSIDE the container.
#docker run -it --entrypoint /bin/bash tui-guess-the-number-bots-i

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
#uv run python -m src.tui-guess-the-number-bots




#docker tag tui-guess-the-number-bots-i alexberkovich/tui-guess-the-number-bots:0.0.1
#docker tag tui-guess-the-number-bots-i alexberkovich/tui-guess-the-number-bots:latest
#docker push alexberkovich/tui-guess-the-number-bots:0.0.1
#docker push alexberkovich/tui-guess-the-number-bots:latest


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
# docker rm -f tui-guess-the-number-bots
# docker rmi -f tui-guess-the-number-bots-i

# docker build --no-cache . -t tui-guess-the-number-bots-i
# docker build --no-cache --progress=plain . -t tui-guess-the-number-bots-i

# docker run --rm -it tui-guess-the-number-bots-i bash
# docker exec -it $(docker ps -q -n=1) bash

# sudo docker stats | sudo tee -a docker_stats.log
# sudo watch -n 15 "docker stats --no-stream | sudo tee -a docker_stats.log"
# RAM+SWAP memory
# watch -n 1 free -h




