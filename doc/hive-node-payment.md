# Payment

## Get payment version 
```YAML
HTTP: GET 
URL: api/v1/payment/version
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
return:
    Success:
        {
            "_status": "OK",
            "version": "1.0"
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

## Get vault service package payment info
```YAML
HTTP: GET
URL: api/v1/payment/vault_package_info
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
return:
    Success:
        {
        "_status": "OK",
        "backupPlans": [
        {
        "amount": 0,
        "currency": "ELA",
        "maxStorage": 500,
        "name": "Free",
        "serviceDays": -1
        },
        {
        "amount": 1.5,
        "currency": "ELA",
        "maxStorage": 2000,
        "name": "Rookie",
        "serviceDays": 30
        },
        {
        "amount": 3,
        "currency": "ELA",
        "maxStorage": 5000,
        "name": "Advanced",
        "serviceDays": 30
        }
        ],
        "paymentSettings": {
        "receivingELAAddress": "ETJqK7o7gBhzypmNJ1MstAHU2q77fo78jg",
        "wait_payment_timeout": 30,
        "wait_tx_timeout": 120
        },
        "pricingPlans": [
        {
        "amount": 0,
        "currency": "ELA",
        "maxStorage": 500,
        "name": "Free",
        "serviceDays": -1
        },
        {
        "amount": 2.5,
        "currency": "ELA",
        "maxStorage": 2000,
        "name": "Rookie",
        "serviceDays": 30
        },
        {
        "amount": 5,
        "currency": "ELA",
        "maxStorage": 5000,
        "name": "Advanced",
        "serviceDays": 30
        }
        ],
        "version": "1.0"
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

## Get vault service pricing plan by name
```YAML
HTTP: GET 
URL: api/v1/payment/vault_pricing_plan?name=Rookie
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
return:
    Success:
        {
            "_status": "OK",
            "name": "Rookie",
            "maxStorage": 2000,
            "serviceDays": 30,
            "amount": 2.5,
            "currency": "ELA"
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

## Get vault backup service pricing plan by name
```YAML
HTTP: GET 
URL: api/v1/payment/vault_backup_plan?name=Rookie
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
return:
    Success:
        {
            "_status": "OK",
            "name": "Rookie",
            "maxStorage": 2000,
            "serviceDays": 30,
            "amount": 2.5,
            "currency": "ELA"
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

## Create payment order
```YAML
HTTP: POST
URL: /api/v1/payment/create_vault_package_order
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data: 
    {
      "pricing_name": "Rookie",
    } 
    to create a vault service order
    {
      "backup_name": "Rookie",
    } 
    to create a vault backup service order

return:
    Success:
      {
        "_status": "OK",
        "order_id": "5f910273dc81b7a0b3f585fc"
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

## Pay vault service package order
```YAML
HTTP: POST
URL: /api/v1/payment/pay_vault_package_order
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data: 
    {
      "order_id": "5f910273dc81b7a0b3f585fc",
      "pay_txids": [
        "0xablcddd",
        "0xablcdef"
      ]
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

## Get order info of vault service purchase
```YAML
HTTP: GET
URL: api/v1/payment/vault_package_order?order_id=5f910273dc81b7a0b3f585fc
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
return:
    Success:
        {
            "_status": "OK",
            "order_info":
            { 
                "order_id":"5f910273dc81b7a0b3f585fc", 
                "did":"did:elastos:ioLFi22fodmFUAFKia6uTV2W8Jz9vEcQyP",
                "app_id":"appid",
                "pricing_info":{
                    "name": "Rookie",
                    "maxStorage": 2000,
                    "serviceDays": 30,
                    "amount": 2.5,
                    "currency": "ELA"
                },
                "pay_txids": [
                    "0xablcddd",
                    "0xablcdef"
                ],
                "state": "wait_tx",//wait_pay, wait_tx, wait_pay_timeout, wait_tx_timeout, failed, success
                "type": "backup", // vault, backup
                "creat_time": 1602236316,
                "finish_time": 1602236366
            }
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

## Get user order info list of vault service purchase
```YAML
HTTP: GET
URL: api/v1/payment/vault_package_order_list
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
return:
    Success:
        {
            "_status": "OK",
            "order_info_list":[
                { 
                    "order_id":"5f910273dc81b7a0b3f585fc", 
                    "did":"did:elastos:ioLFi22fodmFUAFKia6uTV2W8Jz9vEcQyP",
                    "app_id":"appid",
                    "pricing_info":{
                        "name": "Rookie",
                        "maxStorage": 2000,
                        "serviceDays": 30,
                        "amount": 2.5,
                        "currency": "ELA"
                    },
                    "pay_txids": [
                        "0xablcddd",
                        "0xablcdef"
                    ],
                    "type": "vault",
                    "state": "wait_tx",//wait_pay, wait_tx, wait_pay_timeout, wait_tx_timeout, failed, success 
                    "creat_time": 1602236316,
                    "finish_time": 1602236366
                }
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

