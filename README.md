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

# Run Elastos Hive Node
- Copy example environment file
```
cp .env.example .env
```
- Modify .env file with your own values
- [OPTIONAL]: If you want to remove previous mongodb data and start fresh, remove the mongodb directory
```
rm -rf .mongodb-data
```
- Set system environment variables LD_LIBRARY_PATH to hive/util/did/
- Start API server
```
./run.sh start
```

The server will run on url like: http://127.0.0.1:5000
