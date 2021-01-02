#!/usr/bin/env bash

function start_db () {
    docker network create hive
    docker container stop hive-mongo || true && docker container rm -f hive-mongo || true
    docker run -d --name hive-mongo                     \
        --net hive                                  \
        -v ${PWD}/.mongodb-data:/data/db                \
        -p 27020:27017                                  \
        mongo

    echo "start_db ok"
}

#start_db

export HIVE_CONFIG="./.env2"
python ../manage.py runserver

