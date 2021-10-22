#!/usr/bin/env bash

_max_period=30
wait_period=0
echo "Wait until node is ready..."
while ! curl -s http://127.0.0.1:5000/api/v2/about/version >/dev/null
do
    echo "Not ready, still wait ..."
    wait_period=$(($wait_period+1))
    if [ $wait_period -gt $_max_period ];then
       echo "Failed wait in $_max_period seconds, exiting now.."
       break
    else
       sleep 1
    fi
done
