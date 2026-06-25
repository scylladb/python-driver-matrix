#!/usr/bin/env bash
set -e

help_text="
Script to run python driver matrix from within docker

    Optional values can be set via environment variables
    PYTHON_MATRIX_DIR, TOOLS_JAVA_DIR, JMX_DIR, CCM_DIR, SCYLLA_DBUILD_SO_DIR, PYTHON_DRIVER_DIR, INSTALL_DIRECTORY

    ./run_test.sh python3 main.py ../python-driver ../scylla
"

here="$(realpath $(dirname "$0"))"
DOCKER_IMAGE="$(<"$here/image")"

export PYTHON_MATRIX_DIR=${PYTHON_MATRIX_DIR:-`pwd`}
export PYTHON_DRIVER_DIR=${PYTHON_DRIVER_DIR:-`pwd`/../python-driver}
export INSTALL_DIRECTORY=${INSTALL_DIRECTORY:-`pwd`/../scylla}
export CASSANDRA_DIR=${CASSANDRA_DIR:-$INSTALL_DIRECTORY/build/release}
export TOOLS_JAVA_DIR=${TOOLS_JAVA_DIR:-`pwd`/../scylla-tools-java}
export JMX_DIR=${JMX_DIR:-`pwd`/../scylla-jmx}
export DTEST_DIR=${DTEST_DIR:-`pwd`}
export CCM_DIR=${CCM_DIR:-`pwd`/../scylla-ccm}
export SCYLLA_DBUILD_SO_DIR=${SCYLLA_DBUILD_SO_DIR:-${INSTALL_DIRECTORY}/dynamic_libs}
export PIP_CACHE_DIR=${PIP_CACHE_DIR:-${HOME}/.pip-cache}
export UV_CACHE_DIR=${UV_CACHE_DIR:-${HOME}/.uv-cache}


if [[ ! -d ${PYTHON_MATRIX_DIR} ]]; then
    echo -e "\e[31m\$PYTHON_MATRIX_DIR = $PYTHON_MATRIX_DIR doesn't exist\e[0m"
    echo "${help_text}"
    exit 1
fi
if [[ ! -d ${CCM_DIR} ]]; then
    echo -e "\e[31m\$CCM_DIR = $CCM_DIR doesn't exist\e[0m"
    echo "${help_text}"
    exit 1
fi

mkdir -p ${HOME}/.ccm
mkdir -p ${HOME}/.local/lib
mkdir -p ${HOME}/.config
mkdir -p ${HOME}/.docker
mkdir -p ${PIP_CACHE_DIR}
mkdir -p ${UV_CACHE_DIR}

# export all BUILD_* env vars into the docker run
BUILD_OPTIONS=$(env | sed -n 's/^\(BUILD_[^=]\+\)=.*/--env \1/p')
# export all JOB_* env vars into the docker run
JOB_OPTIONS=$(env | sed -n 's/^\(JOB_[^=]\+\)=.*/--env \1/p')
# export all AWS_* env vars into the docker run
AWS_OPTIONS=$(env | sed -n 's/^\(AWS_[^=]\+\)=.*/--env \1/p')

# if in jenkins also mount the workspace into docker
if [[ -d ${WORKSPACE} ]]; then
WORKSPACE_MNT="-v ${WORKSPACE}:${WORKSPACE}"
else
WORKSPACE_MNT=""
fi

DOCKER_CONFIG_MNT="-v $(eval echo ~${USER})/.docker:${HOME}/.docker"

if [[ -z ${SCYLLA_VERSION} ]]; then

    if [[ ! -d ${TOOLS_JAVA_DIR} ]]; then
        echo -e "\e[31m\$TOOLS_JAVA_DIR = $TOOLS_JAVA_DIR doesn't exist\e[0m"
        echo "${help_text}"
        exit 1
    fi
    if [[ ! -d ${JMX_DIR} ]]; then
        echo -e "\e[31m\$JMX_DIR = $JMX_DIR doesn't exist\e[0m"
        echo "${help_text}"
        exit 1
    fi

    if [[ ! -d ${SCYLLA_DBUILD_SO_DIR} ]]; then
        echo "scylla was built with dbuild, and SCYLLA_DBUILD_SO_DIR wasn't supplied or exists"
        cd ${INSTALL_DIRECTORY}
        set +e
        ./tools/toolchain/dbuild -v ${PYTHON_MATRIX_DIR}/scripts/dbuild_collect_so.sh:/bin/dbuild_collect_so.sh -- dbuild_collect_so.sh build/`basename ${CASSANDRA_DIR}`/scylla dynamic_libs/
        set -e
        cd -
    fi

    DOCKER_COMMAND_PARAMS="
    -v ${INSTALL_DIRECTORY}:${INSTALL_DIRECTORY} \
    -v ${TOOLS_JAVA_DIR}:${TOOLS_JAVA_DIR} \
    -v ${JMX_DIR}:${JMX_DIR} \
    -e SCYLLA_DBUILD_SO_DIR \
    -e CASSANDRA_DIR \
    -e INSTALL_DIRECTORY
    "

else
    # export all SCYLLA_* env vars into the docker run
    SCYLLA_OPTIONS=$(env | sed -n 's/^\(SCYLLA_[^=]\+\)=.*/--env \1/p')

    DOCKER_COMMAND_PARAMS="
    ${SCYLLA_OPTIONS} \
    -e MAPPED_SCYLLA_VERSION \
    -e EVENT_LOOP_MANAGER=libev
    "
fi

group_args=()
for gid in $(id -G); do
    group_args+=(--group-add "$gid")
done



run_test_cmd=$(printf '%q ' "$@")

container_cmd=$(cat <<'EOF'
set -e
pip install --user -e __CCM_DIR__
export PATH="$PATH:${HOME}/.local/bin"
export PYTHONPATH="__CCM_DIR__:${PYTHONPATH:-}"
python3 - <<'PY'
import ccmlib.scylla_repository as sr
print(f"CCM repository module: {sr.__file__}")
PY
set +e
__RUN_TEST_CMD__
status=$?
if command -v uv >/dev/null 2>&1; then
    uv cache prune --ci || true
fi
exit "${status}"
EOF
)
container_cmd=${container_cmd//__CCM_DIR__/${CCM_DIR}}
container_cmd=${container_cmd/__RUN_TEST_CMD__/${run_test_cmd}}

docker_cmd="docker run --init --detach=true \
    ${WORKSPACE_MNT} \
    ${DOCKER_COMMAND_PARAMS} \
    ${DOCKER_CONFIG_MNT} \
    -v ${PYTHON_MATRIX_DIR}:${PYTHON_MATRIX_DIR} \
    -v ${PYTHON_DRIVER_DIR}:${PYTHON_DRIVER_DIR} \
    -v ${CCM_DIR}:${CCM_DIR} \
    -e HOME \
    -e SCYLLA_EXT_OPTS \
    -e LC_ALL=en_US.UTF-8 \
    -e DEV_MODE \
    -e PIP_CACHE_DIR \
    -e UV_CACHE_DIR \
    -e WORKSPACE \
    ${BUILD_OPTIONS} \
    ${JOB_OPTIONS} \
    ${AWS_OPTIONS} \
    -w ${PYTHON_MATRIX_DIR} \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v /sys/fs/cgroup:/sys/fs/cgroup:ro \
    -v /etc/passwd:/etc/passwd:ro \
    -v /etc/group:/etc/group:ro \
    -u $(id -u ${USER}):$(id -g ${USER}) \
    ${group_args[@]} \
    --tmpfs ${HOME}/.cache \
     --tmpfs ${HOME}/.shiv \
    --tmpfs ${HOME}/.config \
    --tmpfs ${HOME}/.cassandra \
    -v ${PIP_CACHE_DIR}:${PIP_CACHE_DIR} \
    -v ${UV_CACHE_DIR}:${UV_CACHE_DIR} \
    -v ${HOME}/.local:${HOME}/.local \
    -v ${HOME}/.ccm:${HOME}/.ccm \
    --network=host --privileged \
    ${DOCKER_IMAGE} bash -c $(printf '%q' "$container_cmd")"

echo "Running Docker: $docker_cmd"
container=$(eval $docker_cmd)


kill_it() {
    if [[ -n "$container" ]]; then
        docker rm -f "$container" > /dev/null
        container=
    fi
}

trap kill_it SIGTERM SIGINT SIGHUP EXIT

docker logs "$container" -f

if [[ -n "$container" ]]; then
    exitcode="$(docker wait "$container")"
else
    exitcode=99
fi

echo "Docker exitcode: $exitcode"

kill_it

trap - SIGTERM SIGINT SIGHUP EXIT

# after "docker kill", docker wait will not print anything
[[ -z "$exitcode" ]] && exitcode=1

exit "$exitcode"
