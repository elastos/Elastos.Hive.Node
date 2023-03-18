from src.modules.database.mongodb_collection import mongodb_collection, MongodbCollection
from src.utils.consts import COL_IPFS_CID_REF, COL_IPFS_CID_REF_CID, COL_IPFS_CID_REF_COUNT


@mongodb_collection(COL_IPFS_CID_REF, is_management=True, is_internal=True)
class CollectionIpfsCidRef(MongodbCollection):
    """ This class represents the references of the cid in the files service. """

    def __init__(self, col):
        MongodbCollection.__init__(self, col, is_management=True)

    def increase_cid_ref(self, cid: str, count=1):
        """ directly increase count if exists, else set count """

        filter_ = {COL_IPFS_CID_REF_CID: cid}
        update = {
            '$inc': {COL_IPFS_CID_REF_COUNT: count},  # increase count when exists, else set to count
        }

        self.update_one(filter_, update, upsert=True)

    def decrease_cid_ref(self, cid: str, count=1):
        """ decrease count if not to zero, else to remove cid info
        :return: whether the cid removed.
        """

        filter_ = {COL_IPFS_CID_REF_CID: cid}

        # check if exists
        doc = self.find_one(filter_)
        if not doc:
            return True

        # delete or decrease
        if doc[COL_IPFS_CID_REF_COUNT] <= count:
            self.delete_one(filter_)
            return True
        else:
            update = {'$inc': {COL_IPFS_CID_REF_COUNT: -count}}
            self.update_one(filter_, update)
            return False
