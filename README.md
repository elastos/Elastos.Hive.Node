Elastos Hive Node Service
===========================
[![Build Status](https://travis-ci.com/elastos/Elastos.NET.Hive.Node.svg?token=Jzerup7zXNsvF2i32hZN&branch=master)](https://travis-ci.com/elastos/Elastos.NET.Hive.Node)

## Summary

Elastos Hive is an essential service infrastructure as a decentralized network of Hive nodes presenting data storage capabilities to dApps. And Hive nodes could be deployed to run by anyone or any organization.

To developers, we strongly recommend applications to integrate the **Client SDKs (Java/Swift)** to use the vault service from Hive Nodes instead of directly using the Restful APIs.

#### 1. Three Level of APIs 

There will be the following category of APIs to Client SDKs:
  - Global APIs to query the information related to Nodes;

  - Management APIs for vault/backup lifecycles and payment subscription that could be called authorized applications;

  - Vault services access APIs to general applications.

#### 2. The features for vault service

To the general applications, it would support the following types of data storage services:
- Upload/download files;
- Structured data object access and store onto MongoDB;
- Customized Scripting to select other users to read or contribute the data.

Elastos Hive will keep the promise that **users remain in full control of their own data** and committing the practice on it.

## Deploy Hive with Docker on Ubuntu/Debian system

#### 1. Prerequisites Installed (Docker and Python3)
Assumed the Docker and Python3 already shipped on your system. Otherwise, you need to install them manually. Generally, there is python3.6 already built inside Ubuntu 18.04.  To Docker, you can run the following commands to install it:

```shell
$ curl -fsSL https://get.docker.com -o get-docker.sh
$ sudo sh get-docker.sh
$ sudo usermod -aG docker your-userid
```
***Notice here:*** *you will need to sign out from the target server and log in again to make Docker work effectively.*

#### 2. Download package and unzip it
Download the latest version of packages and untar it onto your server. At the time of this writing, you can run the commands as below:

```shell
$ curl -fsL https://github.com/elastos/Elastos.NET.Hive.Node/archive/release-v2.0.1.tar.gz -o release.tar.gz
$ tar -xzvf release.tar.gz 
```
#### 3. Start the installation
Enter into the source code folder, directly run the command to install the Hive node service:

```shell
$ /bin/bash -c “$(curl -fsSL https://www.trinity-tech.io/hivenode/scripts/run.sh)" -s docker
```
After all the stuff has been finished, use the next command to check whether the Hive Node can work or not.  In the case of success, it will display two container instances. One is hive-node, and the other is mongodb.
```shell
$ docker ps
```
#### 4. Run the test-cases
Run the next command to launch test-cases to verify the deployed node at the same device:

```shell
./run.sh test
```
## Deploy Hive without Docker involved
Coming soon



## Verify the deployed node

After you deployed the Hive node in either way above, you can use curl to check whether it works or not with the following scheme command:

```shell
$ curl -XPOST  -H "Content-Type: application/json" -d '{"key":"value"}' http://your-hive-node-ipaddress:5000/api/v1/echo
```
which would return something below in case that it's been running.
```json
{"key":"value"}
```
You also can open the Browser to input the following URL to see the version of Hive node:
```http
http://your-hive-node-ip-address:5000/api/v1/hive/version
```


## Thanks

Sincerely thanks to all teams and projects that we rely on directly or indirectly.
## Contribution
We welcome contributions to the Elastos Hive Java Project.
## License
MIT

