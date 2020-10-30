# Elastos Hive Node

[![Build Status](https://travis-ci.com/elastos/Elastos.NET.Hive.Node.svg?token=Jzerup7zXNsvF2i32hZN&branch=master)](https://travis-ci.com/elastos/Elastos.NET.Hive.Node)

To start, clone Elastos.NET.Hive.Node repo
```
git clone https://gitlab.com/elastos/Elastos.NET.Hive.Node.git;
cd Elastos.NET.Hive.Node;
```

# Prerequisites
- Install docker at [https://docs.docker.com/get-docker/](https://docs.docker.com/get-docker/)
- Install required packages[Only needs to be done once]
```
./install.sh
```

# Set up
- Copy example environment file to /etc/hive/.env or in your project directory.
```
cp .env.example .env
```
-  If you want change the ".env" file to other directory, you should export the file path in "$HIVE_CONFIG"
```
export $HIVE_CONFIG="/etc/hive/.env"
```

- Modify .env file with your own values. Please note that "172.17.0.1" means "localhost" but lets us access it from inside 
docker container as well as it's a docker dedicated localhost IP
- [OPTIONAL]: If you want to remove previous mongodb data and start fresh, remove the mongodb directory
```
docker container rm -f hive-mongo
rm -rf .mongodb-data
```

# Option 1: Run Elastos Hive Node locally
- [OPTIONAL]: If you want to remove data directory and start from scratch:
```
rm -rf data
```
- Start API server
```
./run.sh direct
```

# Option 2: Run Elastos Hive Node on Docker
- Build docker image
``` 
docker build -t elastos/hive-node .
```
- [OPTIONAL]: If you want to remove data directory and start from scratch:
```
# Note that docker uses ".data" while directly running on the host uses "data" directory
rm -rf .data
```
- Modify the .env file if needed(You may need to modify the value 'MONGO_HOST' and 'MONGO_PORT' to your host IP)
```
# Since the two docker containers run on the same network called "hive", we can directly use their name
# as the host and the native port
MONGO_HOST=hive-mongo
MONGO_PORT=27017
```
- Run docker container
```
./run.sh docker 
```
        
The server will run on url like: http://127.0.0.1:5000

# Test
- [OPTIONAL]: If you want to remove previous mongodb data and start fresh, remove the mongodb directory
```
docker container rm -f hive-mongo
rm -rf .mongodb-data
```
- [OPTIONAL]: Make sure to remove the previous data directory if you want
```
rm -rf data test_did_user_data
```
Run all the tests in order
```
./run.sh test
```

# Verify some common APIs
- Simple API to check whether the API server is running correctly
```
curl -XPOST  -H "Content-Type: application/json" -d '{"key":"value"}' http://localhost:5000/api/v1/echo
```
should return something like
```
{"key":"value"}
```
