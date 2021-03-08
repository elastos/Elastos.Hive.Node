#Pub/Sub

## publish a pub/sub channel
```YAML
HTTP: POST
URL: /api/v1/pubsub/publish
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data: 
    {
        "channel_name": "some_talking_channel"
    } 
return:
    Success:
      {
        "_status": "OK",
      }
    Failure: 
        {
          "_status": "ERR",
          "_error": {
            "code": 401,
            "message": "Error message"
          }
        }
```

## remove a pub/sub channel
```YAML
HTTP: POST
URL: /api/v1/pubsub/remove
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data: 
    {
        "channel_name": "some_talking_channel"
    } 
return:
    Success:
      {
        "_status": "OK",
      }
    Failure: 
        {
          "_status": "ERR",
          "_error": {
            "code": 401,
            "message": "Error message"
          }
        }
```

## get pub/sub channels
```YAML
HTTP: GET
URL: /api/v1/pubsub/channels
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
return:
    Success:
      {
        "_status": "OK",
        channels = [
            "channel_1",
            "channel_2",
            "channel_3"
        ]
      }
    Failure: 
        {
          "_status": "ERR",
          "_error": {
            "code": 401,
            "message": "Error message"
          }
            }
```


## subscribe  a pub/sub channel
```YAML
HTTP: POST
URL: /api/v1/pubsub/subscribe
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data: 
    {
        "pub_did": "elastos:did:xxxxxxxx",
        "pub_app_id": "some data for appid",
        "channel_name": "some_talking_channel"
    } 
return:
    Success:
      {
        "_status": "OK",
      }
    Failure: 
        {
          "_status": "ERR",
          "_error": {
            "code": 401,
            "message": "Error message"
          }
        }
```

## unsubscribe a pub/sub channel
```YAML
HTTP: POST
URL: /api/v1/pubsub/unsubscribe
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data: 
    {
        "pub_did": "elastos:did:xxxxxxxx",
        "pub_app_id": "some data for appid",
        "channel_name": "some_talking_channel"
    } 
return:
    Success:
      {
        "_status": "OK",
      }
    Failure: 
        {
          "_status": "ERR",
          "_error": {
            "code": 401,
            "message": "Error message"
          }
        }
```

## push a message to pub/sub channel
```YAML
HTTP: POST
URL: /api/v1/pubsub/push
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data: 
    {
        "channel_name": "some_talking_channel",
        "message: "some message to publish"
    } 
return:
    Success:
      {
        "_status": "OK",
      }
    Failure: 
        {
          "_status": "ERR",
          "_error": {
            "code": 401,
            "message": "Error message"
          }
        }
```

## get a message from pub/sub channel
```YAML
HTTP: POST
URL: api/v1/pubsub/pop
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data: 
    {
        "pub_did": "elastos:did:xxxxxxxx",
        "pub_app_id": "some data for appid",
        "channel_name": "some_talking_channel",
        "message_limit": 10
    } 
return:
    Success:
        {
            "_status": "OK",
            "messages":[
                {"message":"message1", "time":1614919830},
                {"message":"message2", "time":1614919835}
            ]
        }
    Failure:
        {
          "_status": "ERR",
          "_error": {
            "code": 401,
            "message": "Error message"
          }
        }
```
