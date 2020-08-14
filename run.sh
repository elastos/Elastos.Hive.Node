#!/usr/bin/env bash

function start () {
    docker container stop hive-mongo || true && docker container rm -f hive-mongo || true
    docker run -d --name hive-mongo                     \
        -v ${PWD}/.mongodb-data:/data/db                \
        -p 27020:27017                                  \
        mongo

    echo $1
    if [ ! "$1" = "docker" ]
    then
      echo "Running directly on the machine..."
      ps -ef | grep gunicorn | awk '{print $2}' | xargs kill -9

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
    else
      echo "Running using docker..."
      docker container stop hive-node || true && docker container rm -f hive-node || true
      docker run --name hive-node                     \
        -v ${PWD}/.data:/src/data               \
        -v ${PWD}/.env:/src/.env                \
        -p 5000:5000                                  \
        elastos/hive-node
    fi
}

case "$1" in
    direct)
        start
        ;;
    docker)
        start docker
        ;;
    *)
    echo "Usage: run.sh {docker|direct}"
    exit 1
esac