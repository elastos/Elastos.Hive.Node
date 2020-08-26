#!/usr/bin/env bash

function start_db () {
    docker container stop hive-mongo || true && docker container rm -f hive-mongo || true
    docker run -d --name hive-mongo                     \
        --network hive                                  \
        -v ${PWD}/.mongodb-data:/data/db                \
        -p 27020:27017                                  \
        mongo
}

function start_docker () {
    docker network create hive

    start_db

    echo "Running using docker..."
    docker container stop hive-node || true && docker container rm -f hive-node || true
    docker build -t elastos/hive-node .
    docker run --name hive-node               \
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

    LD_LIBRARY_PATH="$PWD/hive/util/did/" python manage.py runserver
}

function test () {
    docker network create hive

    start_db

    # Run tests
    pytest --disable-pytest-warnings -xs tests/hive_auth_test.py
    pytest --disable-pytest-warnings -xs tests/hive_sync_test.py
    pytest --disable-pytest-warnings -xs tests/hive_mongo_test.py
    pytest --disable-pytest-warnings -xs tests/hive_file_test.py
}

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
