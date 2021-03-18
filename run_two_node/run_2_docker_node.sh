#!/usr/bin/env bash

function start_db_1() {
    docker container stop hive-mongo-1 && docker container rm -f hive-mongo-1
    docker run -d --name hive-mongo-1 \
        --network hive1 \
        -v ${PWD}/.mongodb-1-data:/data/db \
        -p 27021:27017 \
        mongo:4.4.0

    echo "start_db_1 ok"
}

function start_db_2() {
    docker container stop hive-mongo-2 && docker container rm -f hive-mongo-2
    docker run -d --name hive-mongo-2 \
        --network hive2 \
        -v ${PWD}/.mongodb-2-data:/data/db \
        -p 27022:27017 \
        mongo:4.4.0

    echo "start_db_2 ok"
}

function start_docker_1() {
    docker container stop hive-node-1 || true && docker container rm -f hive-node-1 || true
    docker run -d --name hive-node-1 \
        --network hive1 \
        -v ${PWD}/.data1:/src/data \
        -v ${PWD}/.env1:/src/.env \
        -v ${PWD}/payment_config.json:/src/payment_config.json \
        -p 5002:5000 \
        -p 2121-2122:2121-2122 \
        -p 8301-8400:8301-8400 \
        elastos/hive-node-linux
}

function start_docker_2() {
    docker container stop hive-node-2 || true && docker container rm -f hive-node-2 || true
    docker run -d --name hive-node-2 \
        --network hive2 \
        -v ${PWD}/.data2:/src/data \
        -v ${PWD}/.env2:/src/.env \
        -v ${PWD}/payment_config.json:/src/payment_config.json \
        -p 5003:5000 \
        -p 2123-2124:2123-2124 \
        -p 8401-8500:8401-8500 \
        elastos/hive-node-linux
}

function build_docker() {
    echo "Start build docker..."
    docker build -t elastos/hive-node-linux  -f ../Dockerfile_linux ..
    echo "Build docker end"
}

function start() {
    echo "Running using docker..."
    docker network rm hive1
    docker network create hive1
    docker network rm hive2
    docker network create hive2
    start_db_1
    start_db_2
    start_docker_1
    start_docker_2
}

function start_local_1() {
    echo "Running local 1..."
    start_db_1
    gunicorn -b 0.0.0.0:5002 --reload -p hive1.pid --chdir './..' 'hive:create_app(hive_config=".env1")'
}

function start_local_2() {
    echo "Running local 2..."
    start_db_2
    gunicorn -b 0.0.0.0:5003 --reload -p hive2.pid --chdir './..' 'hive:create_app(hive_config=".env2")'
}




case "$1" in
1)
    start_local_1
    ;;
2)
    start_local_2
    ;;
-b)
    build_docker
    ;;
-bs)
    build_docker
    start
    ;;
*)
    start
    ;;
esac
