from os import environ
from dotenv import load_dotenv

load_dotenv()

class Config:
    ######################### Application Config ######################################
    DEBUG = bool(int(environ.get("CONFIG_DEBUG", "0")))
    ENV = environ.get("CONFIG_ENV", "production")

    #########################   ELASTIC Config   ######################################
    ELASTIC_USER_NAME = environ.get("CONFIG_ELASTIC_USER_NAME", None)
    ELASTIC_PASSWORD = environ.get("CONFIG_ELASTIC_PASSWORD", None)
    ELASTIC_HOST = environ.get("CONFIG_ELASTIC_HOST", "localhost")
    ELASTIC_PORT = int(environ.get("CONFIG_ELASTIC_PORT", 9200))
