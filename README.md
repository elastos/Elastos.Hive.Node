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
- Modify .env file with your own values. Please note that "172.17.0.1" means "localhost" but lets us access it from inside 
docker container as well as it's a docker dedicated localhost IP
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
./run.sh direct
```

# Option 2: Run Elastos Hive Node on Docker
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
./run.sh docker 
```
        
The server will run on url like: http://127.0.0.1:5000

# Test
Run all the tests in order
```
./run.sh test
```