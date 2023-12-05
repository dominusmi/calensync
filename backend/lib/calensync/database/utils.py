import json

import boto3

from calensync.database.model import db, MODELS


CONFIG_CACHE = {}


class DatabaseSession:
    def __init__(self, env: str, session: boto3.Session = None):
        if env in ["local", "test"]:
            configs = {
                "db": "test",
                "username": "yoda",
                "password": "admin",
                "host": "0.0.0.0",
                "port": 5432
            }
        elif env == "prod":
            global CONFIG_CACHE
            if CONFIG_CACHE:
                configs = CONFIG_CACHE
            else:
                if session:
                    secretsmanager = session.client("secretsmanager")
                else:
                    secretsmanager = boto3.client("secretsmanager")

                secret = secretsmanager.get_secret_value(
                    SecretId='calensync-prod/db',
                )
                configs = json.loads(secret["SecretString"])
                CONFIG_CACHE = configs
        else:
            raise SystemError("Environment must be local or prod")

        db.init(
            configs["db"],
            user=configs["username"],
            password=configs["password"],
            host=configs["host"],
            port=configs["port"],
        )
        db.bind(MODELS)
        self.db = db

    def __enter__(self):
        return self.db

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.db.close()


def reset_db():
    for model in MODELS:
        model.drop_table(cascade=True)
    for model in reversed(MODELS):
        model.create_table()
