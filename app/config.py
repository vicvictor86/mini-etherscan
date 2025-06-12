import os
import socket

class AppConfig:

    def clear_config(config):
        # Remove None keys
        _conf = {}
        for key in config.keys():
            if config[key] != None:
                _conf[key] = config[key]
        return _conf

    SQLALCHEMY_DATABASE_URI = "postgresql://{}:{}@{}:{}/{}".format(
        os.getenv("DB_USER"),
        os.getenv("DB_PASSWORD"),
        os.getenv("DB_HOST"),
        os.getenv("DB_PORT"),
        os.getenv("DB_DATABASE_NAME"),
    )
    
        
    DEBUG = os.getenv("DEBUG")
    SECRET_KEY = os.getenv("SECRET_KEY")
    SQLALCHEMY_ECHO = False

