Python Driver Matrix
====================

Running locally
***************

This repository contains wrappers for the python driver tests located in datastax's python driver's repository:

https://github.com/datastax/python-driver

The tests go basically as:

1) Clone the python driver repository above
2) Clone Scylla and build it
3) Clone Scylla-CCM
4) Configure and set Scylla-CCM to start a 1 node cluster
5) Go to python-driver-matrix root directory

Keep in mind that all those repos should be under a same base directory

6) Execute the main.py wrapper like::

    python3 main.py ../python-driver ../scylla --tests tests.integration.standard



Running locally
***************

other option running with docker image::

    export INSTALL_DIRECTORY=/home/fruch/Projects/scylla-next

    # running with anything other then release, this should be added
    # export CASSANDRA_DIR=/home/fruch/Projects/scylla-next/build/debug
    ./scripts/run_test.sh python main.py ../python-driver $INSTALL_DIRECTORY --tests tests.integration.standard --versions 3.9.0 --protocol 3


running with relocatable packages::

    export SCYLLA_VERSION=unstable/master:265
    ./scripts/run_test.sh python main.py ../python-driver --tests tests.integration.standard --versions 3.9.0 --protocol 3 --scylla-version $SCYLLA_VERSION


Uploading docker images
-----------------------

when doing changes to requirements.txt, or any other change to docker image, it can be uploaded like this::

    export MATRIX_DOCKER_IMAGE=scylladb/scylla-python-driver-matrix:python3.8-$(date +'%Y%m%d')
    docker build ./scripts -t ${MATRIX_DOCKER_IMAGE}
    docker push ${MATRIX_DOCKER_IMAGE}
    echo "${MATRIX_DOCKER_IMAGE}" > scripts/image

**Note:** you'll need permissions on the scylladb dockerhub organization for uploading images
