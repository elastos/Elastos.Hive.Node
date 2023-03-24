from src.modules.database.mongodb_collection import mongodb_collection, MongodbCollection, CollectionName, CollectionGenericField


@mongodb_collection(CollectionName.IPFS_CID_REF, is_management=True, is_internal=True)
class CollectionIpfsCidRef(MongodbCollection):
    """ This class represents the references of the cid in the files service. """

    CID = CollectionGenericField.CID
    COUNT = CollectionGenericField.COUNT

    def __init__(self, col):
        MongodbCollection.__init__(self, col, is_management=True)

    def increase_cid_ref(self, cid: str, count=1):
        """ directly increase count if exists, else set count """

        filter_ = {self.CID: cid}
        update = {
            '$inc': {self.COUNT: count},  # increase count when exists, else set to count
        }

        self.update_one(filter_, update, upsert=True)

    def decrease_cid_ref(self, cid: str, count=1):
        """ decrease count if not to zero, else to remove cid info
        :return: whether the cid removed.
        """

        filter_ = {self.CID: cid}

        # check if exists
        doc = self.find_one(filter_)
        if not doc:
            return True

        # delete or decrease
        if doc[self.COUNT] <= count:
            self.delete_one(filter_)
            return True
        else:
            update = {'$inc': {self.COUNT: -count}}
            self.update_one(filter_, update)
            return False
