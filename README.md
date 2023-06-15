# Python Driver Matrix

## Prerequisites
* Python3.8
* pip
* docker
* git
* OpenJDK 8 

#### Installing dependencies
Following commands will install all project dependencies using [Pipenv](https:/e/pipenv.readthedocs.io/en/latest/)


* Updates the package sources list
  ```bash
  sudo apt-get -y update
  ```
* `git` install.
  ```bash
  sudo apt-get install -y git-all
  ```
* `pip` install
  ```bash
  sudo apt-get install -y python3-pip
  ```
* `python` imported packages (Please note that the default `Python` version should be `3.8`)
   ```bash
   apt-get install -y build-essential libssl-dev libffi-dev python3-dev python3.8-venv

   ```

##### Repositories dependencies
All repositories should be under the **same base folder**
```bash
  git clone git@github.com:datastax/python-driver.git datastax-python-driver &
  git clone git@github.com:scylladb/python-driver.git scylla-python-driver &
  git clone git@github.com:scylladb/scylla.git scylla &
  git clone git@github.com:scylladb/scylla-ccm.git scylla-ccm &
  git git@github.com:scylladb/python-driver-matrix.git python-driver-matrix &
  wait
```

## Running locally

* Execute the main.py wrapper like:
  * Running with scylla-python-driver: 
    * Scylla driver:
      ```bash
      # Run all standard tests on latest python-driver tag (--versions 1)
      python3 main.py ../scylla-python-driver ../scylla --tests tests.integration.standard --driver-type scylla --versions 1 --protocols 3,4

      # Run all standard tests with specific python-driver tag (--versions 3.25.0-scylla)
      python3 main.py ../scylla-python-driver ../scylla --tests tests.integration.standard --driver-type scylla --versions 3.25.0-scylla --protocols 3,4
      ```
    * Datastax driver:
      ```bash
      # Run all standard tests on latest python-driver tag (--versions 1)
      python3 main.py ../datastax-python-driver ../scylla --tests tests.integration.standard --driver-type datastax --versions 1 --protocols 3,4

      # Run all standard tests with specific python-driver tag (--versions 3.25.0)
      python3 main.py ../datastax-python-driver ../scylla --tests tests.integration.standard --driver-type datastax --versions 3.25.0-scylla --protocols 3,4
      ```
  * Running with docker image: 
    * Scylla driver:
      ```bash
      export INSTALL_DIRECTORY=../scylla

      # running with anything other then release, this should be added
      # export CASSANDRA_DIR=../scylla/build/debug
      ./scripts/run_test.sh python main.py ../scylla-python-driver $INSTALL_DIRECTORY --tests tests.integration.standard --driver-type scylla --versions 3.25.0 --protocol 3,4
      ```
    * Datastax driver:
      ```bash
      export INSTALL_DIRECTORY=../scylla

      # running with anything other then release, this should be added
      # export CASSANDRA_DIR=../scylla/build/debug
      ./scripts/run_test.sh python main.py ../datastax-python-driver $INSTALL_DIRECTORY --tests tests.integration.standard --driver-type datastax --versions 3.25.0 --protocol 3,4
      ```
  * Running with relocatable packages:
    * Scylla driver:
      ```bash
      export SCYLLA_VERSION=unstable/master:2021-12-16T09:10:53Z
      ./scripts/run_test.sh python main.py ../scylla-python-driver --tests tests.integration.standard --driver-type scylla --versions 3.25.0 --protocol 3,4 --scylla-version $SCYLLA_VERSION
      ```
    * Datastax driver:
      ```bash
      export SCYLLA_VERSION=unstable/master:2021-12-16T09:10:53Z
      ./scripts/run_test.sh python main.py ../datastax-python-driver --tests tests.integration.standard --driver-type datastax --versions 3.25.0 --protocol 3,4 --scylla-version $SCYLLA_VERSION
      ```
    export SCYLLA_VERSION=unstable/master:265
    ./scripts/run_test.sh python main.py ../python-driver --tests tests.integration.standard --versions 3.9.0 --protocol 3 --scylla-version $SCYLLA_VERSION
  * Running from PyCharm:
    - Create a basic Python configure.
    - Working directory value is: `/home/oren/Desktop/github/python-driver-matrix`
    - Script path value is: `main.py`
    - Parameters value are:
      ```bash
      /home/oren/Desktop/github/python-driver /home/oren/Desktop/github/scylla
       --driver-type scylla
       --scylla-version unstable/master/2022-01-03T13_22_36Z
       --versions 1
      ```
    - Environment variables are:
      ```bash
      PYTHONUNBUFFERED=1;
      MAPPED_SCYLLA_VERSION=3.11.4
      ```

#### Uploading docker images
When doing changes to `requirements.txt`, or any other change to docker image, it can be uploaded like this:
```bash
    export MATRIX_DOCKER_IMAGE=scylladb/scylla-python-driver-matrix:python3.11-$(date +'%Y%m%d')
    docker build ./scripts -t ${MATRIX_DOCKER_IMAGE}
    docker push ${MATRIX_DOCKER_IMAGE}
    echo "${MATRIX_DOCKER_IMAGE}" > scripts/image
```
**Note:** you'll need permissions on the scylladb dockerhub organization for uploading images
