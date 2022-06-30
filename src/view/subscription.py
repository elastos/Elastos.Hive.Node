# -*- coding: utf-8 -*-

"""
The view of subscription module.
"""
from flask_restful import Resource

from src.utils.http_exception import InvalidParameterException
from src.utils.http_request import RV
from src.modules.ipfs.ipfs_backup_server import IpfsBackupServer
from src.modules.subscription.subscription import VaultSubscription


class VaultPricePlan(Resource):
    def __init__(self):
        self.vault_subscription = VaultSubscription()

    def get(self):
        """ Get an available pricing plan list or the specific pricing plan for the vault and backup service.

        The pricing plan list is the pricing plans that the hive node supported for the vault service.
        The owner of the vault service can use the pricing plan name upgrade the vault service
        to get much more storage space.

        .. :quickref: 02 Subscription; Get Vault Pricing Plans.

        **URL Parameters**:

        .. sourcecode:: http

            subscription=all # possible value: all, vault or backup
            name=rookie # the pricing plan name

        **Response OK**:

        .. sourcecode:: http

            HTTP/1.1 200 OK

        .. code-block:: json

            {
                "backupPlans": [{
                        amount": 0,
                            "currency": "ELA",
                        "maxStorage": 500,
                        "name": "Free",
                        "serviceDays": -1
                    }, {
                        "amount": 1.5,
                        "currency": "ELA",
                        "maxStorage": 2000,
                        "name": "Rookie",
                         "serviceDays": 30
                    }, {
                        "amount": 3,
                         "currency": "ELA",
                        "maxStorage": 5000,
                        "name": "Advanced",
                        "serviceDays": 30
                    }],

                "pricingPlans": [{
                    "amount": 0,
                    "currency": "ELA",
                    "maxStorage": 500,
                    "name": "Free",
                    "serviceDays": -1
                }, {
                    "amount": 2.5,
                    "currency": "ELA",
                    "maxStorage": 2000,
                    "name": "Rookie",
                    "serviceDays": 30
                }, {
                     "amount": 5,
                    "currency": "ELA",
                    "maxStorage": 5000,
                    "name": "Advanced",
                    "serviceDays": 30
                }],
                "version": "1.0"
            }

        **Response Error**:

        .. sourcecode:: http

            HTTP/1.1 401 Unauthorized

        .. sourcecode:: http

            HTTP/1.1 404 Not Found

        """

        subscription = RV.get_args().get_opt('subscription', str, 'all')
        name = RV.get_args().get_opt('name', str, None)

        return self.vault_subscription.get_price_plans(subscription, name)


class VaultInfo(Resource):
    def __init__(self):
        self.vault_subscription = VaultSubscription()

    def get(self):
        """ Get the information of the owned vault service.

        The information contains something like storage usage, pricing plan, etc.

        .. :quickref: 02 Subscription; Get Vault Info.

        **Request**:

        .. sourcecode:: http

            None

        **Response OK**:

        .. sourcecode:: http

            HTTP/1.1 200 OK

        .. code-block:: json

            {
                 “service_did”: “did:elastos:ij8krAVRJitZKJmcCufoLHQjq7Mef3ZjTN"”,
                 “pricing_plan”: “Rookie”,
                 “storage_quota: 524288000,
                 “storage_used”: 20,
                 "start_time": <the epoch time>,
                 "end_time": <the epoch time>,
                 “created”: <the epoch time>,
                 “updated”: <the epoch time>
            }

        **Response Error**:

        .. sourcecode:: http

            HTTP/1.1 401 Unauthorized

        .. sourcecode:: http

            HTTP/1.1 404 Not Found

        """

        # for testing
        files_used = RV.get_args().get_opt('files_used', bool, False)

        return self.vault_subscription.get_info(files_used)


class VaultAppStates(Resource):
    def __init__(self):
        self.vault_subscription = VaultSubscription()

    def get(self):
        """ Get all application stats in the user's vault.

        .. :quickref: 02 Subscription; Get App Stats

        **Request**:

        .. sourcecode:: http

            None

        **Response OK**:

        .. sourcecode:: http

            HTTP/1.1 200 OK

        .. code-block:: json

            {
                "apps": [{
                    "name": <str>,
                    "developer_did": <str>
                    "icon_url": <str>,
                    "redirect_url": <str>,
                    "user_did": <str>,
                    "app_did": <str>,
                    "used_storage_size": <int>
                }]
            }

        **Response Error**:

        .. sourcecode:: http

            HTTP/1.1 400 Bad Request

        .. sourcecode:: http

            HTTP/1.1 401 Unauthorized

        .. sourcecode:: http

            HTTP/1.1 403 Forbidden

        .. sourcecode:: http

            HTTP/1.1 404 Not Found

        """

        return self.vault_subscription.get_app_stats()


class VaultSubscribe(Resource):
    def __init__(self):
        self.vault_subscription = VaultSubscription()

    def put(self):
        """ Subscribe to a remote vault service on the specific hive node,
        where would create a new vault service if no such vault existed against the DID used.

        A user can subscribe to only one vault service on the specific hive node with a given DID,
        then should declare that service endpoint on the DID document that would be published on the DID chain
        so that other users could be aware of the address and access the data on that vault with certain permission.

        The free pricing plan is applied to a new subscribed vault.
        The payment APIs will be used for upgrading the vault service.

        .. :quickref: 02 Subscription; Vault Subscribe

        **Request**:

        .. sourcecode:: http

            None

        **Response OK**:

        .. sourcecode:: http

            HTTP/1.1 200 OK

        .. code-block:: json

            {
                “service_did”: <hive node service did>
                “pricing_plan”: <the using pricing plan>
                “storage_quota”: 50000000, # the max space of the storage for the vault service.
                “storage_used”: 0,
                "start_time": <the epoch time>,
                "end_time": <the epoch time>,
                “created”: <the epoch time>,
                “updated”: <the epoch time>
            }

        **Response Error**:

        .. sourcecode:: http

            HTTP/1.1 401 Unauthorized

        .. sourcecode:: http

            HTTP/1.1 455 Already Exists

        """
        return self.vault_subscription.subscribe()


class VaultActivateDeactivate(Resource):
    def __init__(self):
        self.vault_subscription = VaultSubscription()

    def post(self):
        """ Activate or deactivate the vault

        The vault can only be read when it is deactivated.
        This is very useful for do some operations on vault, like backup, promotion, ect.

        .. :quickref: 02 Subscription; Activate&Deactivate

        **Request**:

        .. sourcecode:: http

            None

        **Response OK**:

        .. sourcecode:: http

            HTTP/1.1 201 Created

        **Response Error**:

        .. sourcecode:: http

            HTTP/1.1 401 Unauthorized

        .. sourcecode:: http

            HTTP/1.1 404 Not Found

        """
        op = RV.get_args().get('op', str)
        if op == 'activation':
            return self.vault_subscription.activate()
        elif op == 'deactivation':
            return self.vault_subscription.deactivate()
        else:
            raise InvalidParameterException(f'Unsupported parameter "op" value {op}')


class VaultUnsubscribe(Resource):
    def __init__(self):
        self.vault_subscription = VaultSubscription()

    def delete(self):
        """ Unsubscribe from the remote vault service on a specific hive node.
        Only the vault owner can unsubscribe from his owned vault service.
        After unsubscription, the vault service would stop rendering service,
        and users can not access data from the vault anymore.

        And the data on the vault would be unsafe and undefined or even deleted from the hive node.

        .. :quickref: 02 Subscription; Vault Unsubscribe

        **Request**:

        .. sourcecode:: http

            None

        **Response OK**:

        .. sourcecode:: http

            HTTP/1.1 204 No Content

        **Response Error**:

        .. sourcecode:: http

            HTTP/1.1 401 Unauthorized

        .. sourcecode:: http

            HTTP/1.1 404 Not Found

        """
        return self.vault_subscription.unsubscribe()


###############################################################################
# blow is for backup.
###############################################################################


class BackupInfo(Resource):
    def __init__(self):
        self.backup_server = IpfsBackupServer()

    def get(self):
        """ Get the information of the owned backup service.

        The information contains something like storage usage, pricing plan, etc.

        .. :quickref: 02 Subscription; Get Backup Info.

        **Request**:

        .. sourcecode:: http

            None

        **Response OK**:

        .. sourcecode:: http

            HTTP/1.1 200 OK

        .. code-block:: json

            {
                 “service_did”: “did:elastos:ij8krAVRJitZKJmcCufoLHQjq7Mef3ZjTN",
                 "pricing_plan": "Rookie",
                 “storage_quota: 500，
                 “storage_used”: 20,
                 “start_time”: 1602236316, // epoch time.
                 “end_time”: 1602236316,
                 “created”: 1602236316,
                 “updated”: 1604914928
            }

        **Response Error**:

        .. sourcecode:: http

            HTTP/1.1 401 Unauthorized

        .. sourcecode:: http

            HTTP/1.1 404 Not Found

        """
        return self.backup_server.get_info()


class BackupSubscribe(Resource):
    def __init__(self):
        self.backup_server = IpfsBackupServer()

    def put(self):
        """ Subscribe to a remote backup service on the specific hive node.
        With the backup service, the data of the vault service can backup for data security.

        .. :quickref: 02 Subscription; Backup Subscribe

        **Request**:

        .. sourcecode:: http

            None

        **Response OK**:

        .. sourcecode:: http

            HTTP/1.1 200 OK

        .. code-block:: json

            {
                 “service_did”: “did:elastos:ij8krAVRJitZKJmcCufoLHQjq7Mef3ZjTN",
                 "pricing_plan": "Rookie",
                 “storage_quota: 500，
                 “storage_used”: 20,
                 “start_time”: 1602236316, // epoch time.
                 “end_time”: 1602236316,
                 “created”: 1602236316,
                 “updated”: 1604914928
            }

        **Response Error**:

        .. sourcecode:: http

            HTTP/1.1 401 Unauthorized

        .. sourcecode:: http

            HTTP/1.1 455 Already Exists

        """
        return self.backup_server.subscribe()


class BackupActivateDeactivate(Resource):
    def __init__(self):
        self.backup_server = IpfsBackupServer()

    def post(self):
        op = RV.get_args().get('op', str)
        if op == 'activation':
            return self.backup_server.activate()
        elif op == 'deactivation':
            return self.backup_server.deactivate()
        else:
            raise InvalidParameterException(f'Unsupported parameter "op" value {op}')


class BackupUnsubscribe(Resource):
    def __init__(self):
        self.backup_server = IpfsBackupServer()

    def delete(self):
        """ Unsubscribe from the remote backup service on a specific hive node.

        The data on the backup node would be unsafe and undefined or even deleted from the hive node.

        .. :quickref: 02 Subscription; Backup Unsubscribe

        **Request**:

        .. sourcecode:: http

            None

        **Response OK**:

        .. sourcecode:: http

            HTTP/1.1 204 No Content

        **Response Error**:

        .. sourcecode:: http

            HTTP/1.1 401 Unauthorized

        .. sourcecode:: http

            HTTP/1.1 404 Not Found

        """
        return self.backup_server.unsubscribe()
