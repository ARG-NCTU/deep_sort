#!/usr/bin/env bash

ARGS=("$@")

PROJ_NAME="deep_sort"

IMG="argnctu/deep_sort"

USER_NAME="arg"
CONTAINER_NAME="deep_sort"

CONTAINER_ID=$(docker ps -aqf "ancestor=${IMG}")
if [ $CONTAINER_ID ]; then
  echo "Attach to docker container $CONTAINER_ID"
  xhost +
  docker exec --privileged -e DISPLAY=${DISPLAY} -e LINES="$(tput lines)" -it ${CONTAINER_ID} bash
  xhost -
  return
fi

# Make sure processes in the container can connect to the x server
# Necessary so gazebo can create a context for OpenGL rendering (even headless)
XAUTH=/tmp/.docker.xauth
if [ ! -f $XAUTH ]; then
  xauth_list=$(xauth nlist $DISPLAY)
  xauth_list=$(sed -e 's/^..../ffff/' <<<"$xauth_list")
  if [ ! -z "$xauth_list" ]; then
    echo "$xauth_list" | xauth -f $XAUTH nmerge -
  else
    touch $XAUTH
  fi
  chmod a+r $XAUTH
fi

# Prevent executing "docker run" when xauth failed.
if [ ! -f $XAUTH ]; then
  echo "[$XAUTH] was not properly created. Exiting..."
  exit 1
fi

# Check for new_extension directory
EXTENSION_DIR=$(find /media/$USER -maxdepth 1 -type d -name "new_extension*" | head -n 1)
EXTENSION_MOUNT=""
if [ -n "$EXTENSION_DIR" ]; then
  EXTENSION_MOUNT="-v $EXTENSION_DIR:/media/arg/new_extension"
fi

docker run \
  -it \
  --rm \
  --runtime=nvidia \
  -e DISPLAY \
  -e XAUTHORITY=$XAUTH \
  -e REPO_NAME=$REPO_NAME \
  -e HOME=/home/${USER_NAME} \
  -e OPENAI_API_KEY=$OPENAI_API_KEY\
  -e NVIDIA_DRIVER_CAPABILITIES=all \
  -e RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
  -v "$XAUTH:$XAUTH" \
  -v "/home/${USER}/${PROJ_NAME}:/home/${USER_NAME}/${PROJ_NAME}" \
  $EXTENSION_MOUNT \
  -v "/tmp/.X11-unix:/tmp/.X11-unix" \
  -v "/etc/localtime:/etc/localtime:ro" \
  -v "/dev:/dev" \
  -v "/var/run/docker.sock:/var/run/docker.sock" \
  -v "/usr/share/vulkan/icd.d/nvidia_icd.json:/usr/share/vulkan/icd.d/nvidia_icd.json" \
  --user "root:root" \
  --workdir "/home/${USER_NAME}/${PROJ_NAME}" \
  --name "${CONTAINER_NAME}" \
  --network host \
  --privileged \
  --security-opt seccomp=unconfined \
  "${IMG}" \
  bash

# -e "TERM=xterm-256color" \