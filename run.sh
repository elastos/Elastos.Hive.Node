#!/usr/bin/env bash

function start () {
    docker container stop hive-mongo || true && docker container rm -f hive-mongo || true
    docker run -d --name hive-mongo                     \
        -v ${PWD}/.mongodb-data:/data/db                \
        -p 27020:27017                                  \
        mongo

    virtualenv -p `which python3.6` .venv
    source .venv/bin/activate
    pip install --upgrade pip

    case `uname` in
    Linux )
        pip install -r requirements.txt
        ;;
    Darwin )
        pip install --global-option=build_ext --global-option="-I/usr/local/include" --global-option="-L/usr/local/lib" -r requirements.txt
        ;;
    *)
    exit 1
    ;;
    esac

    LD_LIBRARY_PATH="$PWD/hive/util/did/" gunicorn -b 0.0.0.0:5000 --reload wsgi:application
}

function stop () {
    docker container stop hive-mongo || true && docker container rm -f hive-mongo || true
    ps -ef | grep gunicorn | awk '{print $2}' | xargs kill -9
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    *)
    echo "Usage: run.sh {start|stop}"
    exit 1
esac