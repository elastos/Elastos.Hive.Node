#!/usr/bin/env bash

echo "Install required packages"

case `uname` in
    Linux )
        sudo apt-get update -y 
        sudo apt-get install build-essential libffi-dev python3.6 python3.6-dev mongo-tools -y
        curl https://rclone.org/install.sh | sudo bash
        PYTHON="python3.6"
        ;;
    Darwin )
        brew update
        brew install sashkab/python/python@3.7 rclone mongodb/brew/mongodb-database-tools
        ln -s /usr/local/opt/python@3.7/bin/python3.7 /usr/local/bin/python3.7
        PYTHON="python3.7"
        ;;
    *)
    exit 1
    ;;
esac

pip3 install virtualenv 

type virtualenv >/dev/null 2>&1 || { echo >&2 "No suitable python virtual env tool found, aborting"; exit 1; }

rm -rf .venv
virtualenv -p `which $PYTHON` .venv
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

