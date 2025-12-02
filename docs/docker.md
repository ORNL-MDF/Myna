---
title: Docker Container
---

To use the containerized version of Myna and it's open-source dependencies, you can
use the Myna Docker container hosted at
[https://github.com/ORNL-MDF/containers](https://github.com/ORNL-MDF/containers).

1. [Install Docker Desktop](https://docs.docker.com/engine/install/) under an
   appropriate license.
2. Open Docker Desktop.
3. Pull the Myna Docker image. In the bottom right of the Docker Desktop window, click
   "Terminal" (if prompted, hit "enable") and enter
   `docker pull ghcr.io/ornl-mdf/containers/ubuntu:dev`. Once completed, the image will
   show up in the "Images" tab of Docker.
4. (Optional) Link your data directory or server to a Docker volume that can be used
   across multiple Docker instances. Use the
   [docker volume create](https://docs.docker.com/reference/cli/docker/volume/create/)
   command, following the documentation for your specific data configuration.
5. (Optional) If you use Visual Studio Code for your development environment, then
   you can install the `Docker` and `Dev Containers` extensions to work with Docker
   containers from within Visual Studio Code.
6. Launch an interactive Docker container to execute code within the Docker environment:
   - **From a command terminal**: `docker run -it ghcr.io/ornl-mdf/containers/ubuntu:dev`
   - **From Visual Studio Code**: Click on the Docker tab on left-hand navigation bar.
     Select the `ghcr.io/ornl-mdf/containers/ubuntu:dev` container, right-click and
     select `Run interactive`. A new entry will appear in the "container" section.
     Right-click the container and select `Attach Visual Studio Code`. For more detailed
     instructions and troubleshooting, see the
     [Docker extension documentation](https://code.visualstudio.com/docs/containers/overview).
7. Within the Docker container, the Myna examples are located at `/opt/myna/examples/`.
   These can be copied to your current working directory with
   `cp -r /opt/myna/examples ./myna_examples`. To run examples, follow the instructions
   at [Getting Started: Using Myna](https://ornl-mdf.github.io/myna-docs/getting_started#using-myna).
