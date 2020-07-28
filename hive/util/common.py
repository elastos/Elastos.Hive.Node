def did_tail_part(did):
    return did.split(":")[2]


def gene_eve_mongo_db_prefix(did, app_id):
    return did_tail_part(did) + "_" + app_id + "_mongo_prefix"


def create_full_path_dir(path):
    try:
        path.mkdir(exist_ok=True, parents=True)
    except Exception as e:
        print("Exception in create_full_path:" + e)
        return False
    return True
