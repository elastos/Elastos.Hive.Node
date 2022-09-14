#!/usr/bin/env bash

if [[ $(uname) == "Darwin" ]]; then
    # mac
    SEDI=(-i '' -e)
else
    # linux
    SEDI=(-i)
fi

function start_db () {
    docker container list --all | grep hive-mongo > /dev/null \
              && docker container stop hive-mongo > /dev/null \
              && docker container rm -f hive-mongo > /dev/null
    echo -n "Hive-Mongo Container: "
    docker run -d --name hive-mongo                     \
        --network hive-service                          \
        -v ${PWD}/.mongodb-data:/data/db                \
        -p 27020:27017                                  \
        mongo:4.4.0 | cut -c -9
}

function start_ipfs() {
    docker container list --all | grep hive-ipfs > /dev/null \
              && docker container stop hive-ipfs > /dev/null \
              && docker container rm -f hive-ipfs > /dev/null
    mkdir -p ${PWD}/.ipfs-data/ipfs-docker-staging ; mkdir -p ${PWD}/.ipfs-data/ipfs-docker-data
    echo -n "Hive-IPFS Container: "
    docker run -d --name hive-ipfs                            \
        --network hive-service                                \
        -v ${PWD}/.ipfs-data/ipfs-docker-staging:/export      \
        -v ${PWD}/.ipfs-data/ipfs-docker-data:/data/ipfs      \
        -p 127.0.0.1:5002:5001                                \
        lscr.io/linuxserver/ipfs | cut -c -9
}

function start_node() {
  docker container list --all | grep hive-node > /dev/null    \
            && docker container stop hive-node > /dev/null    \
            && docker container rm -f hive-node > /dev/null
  docker image rm -f elastos/hive-node
  docker build -t elastos/hive-node . > /dev/null
  mkdir .data
  echo -n "Hive-Node Container: "
  docker run -d --name hive-node    \
      --network hive-service        \
      -v ${PWD}/.data:/src/data     \
      -v ${PWD}/.env:/src/.env      \
      -p 5000:5000                  \
      elastos/hive-node | cut -c -9
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
        pip install markupsafe
        # pip install --global-option=build_ext --global-option="-I/usr/local/include" --global-option="-L/usr/local/lib" -r requirements.txt
        CPPFLAGS=-I/usr/local/opt/openssl/include LDFLAGS=-L/usr/local/opt/openssl/lib ARCHFLAGS="-arch x86_64" \
          pip install --global-option=build_ext --global-option="-I/usr/local/include" --global-option="-L/usr/local/lib" -r requirements.txt
        ;;
    *)
    exit 1
    ;;
    esac
}

function prepare_env_file() {
    if [ -f ".env" ]; then
        echo "[WARNING] .env file is already exists. Try to remove it and restart this script if want to reset."
        return
    fi

    cp config/.env.example .env

    DID_MNEMONIC=$(grep 'DID_MNEMONIC' .env | sed 's/DID_MNEMONIC="//;s/"//')
    echo -n "Your DID MNEMONIC: "
    echo -e "\033[;36m ${DID_MNEMONIC} \033[0m"
    echo -n "Confirm ? (y/n) "
    read RESULT
    RESULT=$(echo ${RESULT})
    if [ ! "${RESULT}" == "y" ];then
        echo -n "Please input your DID MNEMONIC: "
        read DID_MNEMONIC
        DID_MNEMONIC=$(echo ${DID_MNEMONIC})
        [ "${DID_MNEMONIC}" = "" ] && echo "You don't input DID MNEMONIC" && exit 1
        sed "${SEDI[@]}"  "/^DID_MNEMONIC/s/^.*$/DID_MNEMONIC=\"${DID_MNEMONIC}\"/" .env
    fi

    echo -n "Please input your DID MNEMONIC PASSPHRASE: "
    read DID_PASSPHRASE
    DID_PASSPHRASE=$(echo ${DID_PASSPHRASE})
    sed "${SEDI[@]}" "/^DID_PASSPHRASE/s/^.*$/DID_PASSPHRASE=${DID_PASSPHRASE}/" .env

    echo -n "Please input your DID MNEMONIC SECRET: "
    read DID_STOREPASS
    DID_STOREPASS=$(echo ${DID_STOREPASS})
    [ "${DID_STOREPASS}" != "" ] && sed "${SEDI[@]}"  "/^DID_STOREPASS/s/^.*$/DID_STOREPASS=${DID_STOREPASS}/" .env

    sed "${SEDI[@]}"  "/^DID_RESOLVER/s/^.*$/DID_RESOLVER=http:\/\/api.elastos.io:20606/" .env
    sed "${SEDI[@]}"  "/^ELA_RESOLVER/s/^.*$/ELA_RESOLVER=http:\/\/api.elastos.io:20336/" .env
    sed "${SEDI[@]}"  "/^MONGO_HOST/s/^.*$/MONGO_HOST=hive-mongo/" .env
    sed "${SEDI[@]}"  "/^MONGO_PORT/s/^.*$/MONGO_PORT=27017/" .env
    sed "${SEDI[@]}"  "/^IPFS_NODE_URL/s/^.*$/IPFS_NODE_URL=http:\/\/hive-ipfs:5001/" .env
    sed "${SEDI[@]}"  "/^IPFS_PROXY_URL/s/^.*$/IPFS_PROXY_URL=http:\/\/hive-ipfs:8080/" .env
}

function check_docker() {
    echo "Running using docker..."
    docker version > /dev/null 2>&1
    if [ ! $? -eq 0 ];then
        echo "You don't have docker installed. Please run the below commands to install docker"
        echo "
$ curl -fsSL https://get.docker.com -o get-docker.sh
$ sudo sh get-docker.sh
$ sudo usermod -aG docker $(whoami)
        "
        exit
    fi
}

function prepare_before_running() {
    check_docker
    prepare_env_file
    docker network ls | grep hive-service > /dev/null || docker network create hive-service
    start_db
    start_ipfs
}

function start_docker () {
    echo "Running by docker..."
    prepare_before_running
    start_node
    source wait_node.sh
}

function start_direct () {
    echo "Running directly only..."
    prepare_before_running
    setup_venv
    LD_LIBRARY_PATH="$PWD/hive/util/did/" python manage.py runserver
}

function test_v1() {
    pytest --disable-pytest-warnings -xs tests_v1/hive_auth_test.py
    pytest --disable-pytest-warnings -xs tests_v1/hive_subscription_test.py
    pytest --disable-pytest-warnings -xs tests_v1/hive_mongo_test.py
    pytest --disable-pytest-warnings -xs tests_v1/hive_file_test.py
    pytest --disable-pytest-warnings -xs tests_v1/hive_scripting_test.py
    # pytest --disable-pytest-warnings -xs tests_v1/hive_payment_test.py
    # pytest --disable-pytest-warnings -xs tests_v1/hive_backup_test.py
    # pytest --disable-pytest-warnings -xs tests_v1/hive_internal_test.py # INFO: skip this
    # pytest --disable-pytest-warnings -xs tests_v1/hive_pubsub_test.py
}

function test_v2() {
    pytest --disable-pytest-warnings -xs tests/about_test.py
    pytest --disable-pytest-warnings -xs tests/auth_test.py
    pytest --disable-pytest-warnings -xs tests/subscription_test.py
    pytest --disable-pytest-warnings -xs tests/database_test.py
    pytest --disable-pytest-warnings -xs tests/files_test.py
    pytest --disable-pytest-warnings -xs tests/scripting_test.py
    pytest --disable-pytest-warnings -xs tests/payment_test.py
    pytest --disable-pytest-warnings -xs tests/backup_test.py
    pytest --disable-pytest-warnings -xs tests/backup_local_test.py
    pytest --disable-pytest-warnings -xs tests/provider_test.py
}

function test () {
    echo "Running directly only..."
    prepare_before_running
    setup_venv

    rm -rf data
    LD_LIBRARY_PATH="$PWD/src/util/did/" python manage.py runserver &

    test_v1
    test_v2
    pkill -f manage.py
}

function stop() {
    hive_node=$(docker container list --all | grep hive-node | awk '{print $1}')
    if [ -n "${hive_node}" ];then
    	docker container stop ${hive_node}
    	docker container rm ${hive_node}
    fi
    hive_mongo=$(docker container list --all | grep hive-mongo | awk '{print $1}')
    if [ -n "${hive_mongo}" ];then
    	docker container stop ${hive_mongo}
    	docker container rm ${hive_mongo}
    fi
}

case "$1" in
    setup)
        setup_venv
        ;;
    direct)
        start_direct
        ;;
    docker)
        start_docker
        ;;
    test)
        test
        ;;
    test_v1)
        # INFO: run hive node and enter .venv first before run this command.
        test_v1
        ;;
    test_v2)
        # INFO: run hive node and enter .venv first before run this command.
        # example: HIVE_PORT=5000 ./run.sh test_v2
        test_v2
        ;;
    stop)
        stop
        ;;
    *)
    echo "Usage: run.sh {setup|direct|docker|test|test_v1|HIVE_PORT=5000 ./run.sh test_v2|stop}"
    exit 1
esac
