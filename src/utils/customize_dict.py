class ImmutableDict(dict):
    """ Immutable Dict """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __hash__(self):
        return id(self)

    def _immutable(self, *args, **kws):
        raise TypeError('ImmutableDict is immutable')

    __setitem__ = _immutable
    __delitem__ = _immutable
    clear = _immutable
    update = _immutable
    setdefault = _immutable
    pop = _immutable
    popitem = _immutable


class Dotdict(dict):
    """ Base class for all mongodb document.

    if you define a document like this (all keys must be underscored):

        {
            "did": "xxx",
            "max_storage": 2097152000,
            "pricing_using": "Rockie"
        }

    Then you can define class like this. So please just use in the class.

        class Vault(Dotdict):
            def get_user_did():
                return self.did

    Usage like this:

        vault = Vault(**doc)

    """
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__
