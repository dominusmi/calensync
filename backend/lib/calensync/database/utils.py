import json

import boto3
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from calensync.database.model import db, MODELS


CONFIG_CACHE = {}


class DatabaseSession:
    def __init__(self, env: str, session: boto3.Session = None):
        if env in ["local", "test"]:
            if env == "local":
                db_name = "postgres"
            else:
                db_name = "test"
                try:
                    con = psycopg2.connect(dbname='postgres',
                                           user="yoda", host='0.0.0.0',
                                           password="admin")

                    con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)  # <-- ADD THIS LINE

                    cur = con.cursor()

                    # Use the psycopg2.sql module instead of string concatenation
                    # in order to avoid sql injection attacks.
                    cur.execute(sql.SQL("CREATE DATABASE {}").format(
                        sql.Identifier(db_name))
                    )
                except Exception:
                    ...
            configs = {
                "db": db_name,
                "username": "yoda",
                "password": "admin",
                "host": "0.0.0.0",
                "port": 5432
            }

        elif env in ["dev", "prod"]:
            global CONFIG_CACHE
            if CONFIG_CACHE:
                configs = CONFIG_CACHE
            else:
                if session:
                    secretsmanager = session.client("secretsmanager")
                else:
                    secretsmanager = boto3.client("secretsmanager")

                secret = secretsmanager.get_secret_value(
                    SecretId=f'calensync-{env}-db',
                )
                configs = json.loads(secret["SecretString"])
                CONFIG_CACHE = configs
        else:
            raise RuntimeError(f"Invalid environment {env}")

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
