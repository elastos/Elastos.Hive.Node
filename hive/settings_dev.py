from decouple import config

DID_SIDECHAIN_URL = config('DID_SIDECHAIN_URL', default="http://api.elastos.io:21606", cast=str)

MONGO_HOST = config('MONGO_HOST', default="172.17.0.1", cast=str)
MONGO_PORT = config('MONGO_PORT', default=27020, cast=int)
MONGO_DBNAME = "hivedb_dev"

RESOURCE_METHODS = ['GET', 'POST', 'DELETE']

ITEM_METHODS = ['GET', 'PATCH', 'DELETE']

CACHE_CONTROL = 'max-age=20'
CACHE_EXPIRES = 20

URL_PREFIX = 'api/v1/db/col'


DOMAIN = {
}
