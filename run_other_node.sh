#!/usr/bin/env bash

function start_test_db () {
    docker container stop hive-test-mongo  && docker container rm -f hive-test-mongo
    docker run -d --name hive-test-mongo                \
        -v ${PWD}/.mongodb-test-data:/data/db                \
        -p 27022:27017                                  \
        mongo

    echo "start_test_db ok"
}

start_test_db

export HIVE_CONFIG="./.env.test"
python manage.py runserver

