# Elastos Hive Node

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
- Copy example environment file
```
cp .env.example .env
```
- Modify .env file with your own values
- [OPTIONAL]: If you want to remove previous mongodb data and start fresh, remove the mongodb directory
```
rm -rf .mongodb-data
```

# Option 1: Run Elastos Hive Node locally
- [OPTIONAL]: If you want to remove data directory and start from scratch:
```
    rm -rf data
```
- Start API server
```
./run.sh start
```

# Option 2: Run Elastos Hive Node on Docker
- Stop previously running docker container
```
    docker container stop hive-node || true && docker container rm -f hive-node || true
```
- Build docker image
``` 
    docker build -t elastos/hive-node .
```
- [OPTIONAL]: If you want to remove data directory and start from scratch:
```
    rm -rf .data
```
- Run docker container
```
   docker run --name hive-node                     \
        -v ${PWD}/.data:/src/data               \
        -v ${PWD}/.env:/src/.env                \
        -p 5000:5000                                  \
        elastos/hive-node
```
        
The server will run on url like: http://127.0.0.1:5000
