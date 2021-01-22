#!/usr/bin/env bash

function start_db () {
    docker container stop hive-mongo || true && docker container rm -f hive-mongo || true
    docker run -d --name hive-mongo                     \
        --network hive                                  \
        -v ${PWD}/.mongodb-data:/data/db                \
        -p 27020:27017                                  \
        mongo
}

function start_test_db () {
    docker container stop hive-test-mongo || true && docker container rm -f hive-test-mongo || true
    docker run -d --name hive-test-mongo                \
        --network hive                                  \
        -v ${PWD}/.mongodb-test-data:/data/db           \
        -p 27022:27017                                  \
        mongo
}

function setup_venv () {
  echo "setup_venv"
    case `uname` in
    Linux )
        #virtualenv -p `which python3.6` .venv
        python3 -m venv .venv
        source .venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt
        ;;
    Darwin )
        #virtualenv -p `which python3.7` .venv
        python3 -m venv .venv
        source .venv/bin/activate
        pip install --upgrade pip
        pip install --global-option=build_ext --global-option="-I/usr/local/include" --global-option="-L/usr/local/lib" -r requirements.txt
        ;;
    *)
    exit 1
    ;;
    esac
}

function start_docker () {
    docker network create hive

    start_db

    echo "Running using docker..."
    docker container stop hive-node || true && docker container rm -f hive-node || true
    docker build -t elastos/hive-node .
    docker run -d --name hive-node               \
      --network hive                          \
      -v ${PWD}/.data:/src/data                \
      -v ${PWD}/.env:/src/.env                \
      -p 5000:5000                            \
      elastos/hive-node
}

function start_direct () {
    docker network create hive

    start_db

    echo "Running directly on the machine..."
    ps -ef | grep gunicorn | awk '{print $2}' | xargs kill -9

    setup_venv

    LD_LIBRARY_PATH="$PWD/hive/util/did/" python manage.py runserver
}

function test () {
    docker network create hive

    start_db
    start_test_db

    setup_venv

    # Run tests
    pytest --disable-pytest-warnings -xs tests/hive_auth_test.py
    pytest --disable-pytest-warnings -xs tests/hive_mongo_test.py
    pytest --disable-pytest-warnings -xs tests/hive_file_test.py
    pytest --disable-pytest-warnings -xs tests/hive_scripting_test.py
    pytest --disable-pytest-warnings -xs tests/hive_payment_test.py
    pytest --disable-pytest-warnings -xs tests/hive_backup_test.py
    pytest --disable-pytest-warnings -xs tests/hive_internal_test.py

    docker container stop hive-mongo && docker container rm -f hive-mongo
    docker container stop hive-test-mongo && docker container rm -f hive-test-mongo
}

export HIVE_NODE_HOME="."

case "$1" in
    direct)
        start_direct
        ;;
    docker)
        start_docker
        ;;
    test)
        test
        ;;
    *)
    echo "Usage: run.sh {docker|direct|test}"
    exit 1
esac
