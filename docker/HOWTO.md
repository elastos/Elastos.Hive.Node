# 1. HOW TO USE Dockerfile

### Create docker image

Change work directory to $(YOUR-HIVE-DIR)/docker, and run the command:

```shell
$ docker build -t hive-dev .
```

### Start docker image

Run the following command to start docker image to run as Linux container:

```shell
$ docker run -tiv YOUR-HIVE-DIR:/home/elastos/Hive.Node --tmpfs=/tmp hive-dev /bin/bash -c "docker/startup.sh&&bash"
```

