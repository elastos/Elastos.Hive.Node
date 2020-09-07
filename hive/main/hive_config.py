
import os
import pathlib
import configparser

hive_cfg = str(pathlib.Path("." + os.sep + "hive.conf").absolute())

class HiveConfig():
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read(hive_cfg)

    def getDIDValue(self, key, default = None):
        if self.config.has_option('DID', key):
            return self.config['DID'][key]
        return default

    def setDIDValue(self, key, value):
        if not 'DID' in self.config:
            self.config['DID'] = {}
        self.config['DID'][key] = value
        self.saveToFile()

    def getConfig(self):
        return self.config

    def saveToFile(self):
        with open(hive_cfg, 'w') as configfile:
            self.config.write(configfile)



