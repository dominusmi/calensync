import json
import os
import uuid

import boto3
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from calensync.database.model import db, MODELS

CONFIG_CACHE = {}


def get_multiple_parameters(parameter_names: list[str], session: boto3.Session) -> dict[str, str]:
    """
    Retrieve a parameter value from AWS Systems Manager Parameter Store.

    :param parameter_names: List of the names of the parameters to retrieve
    :param session: boto3 session
    :return: The parameter value if successful, None otherwise
    """
    # Create a client for the SSM service
    ssm_client = session.client('ssm')

    # Get the parameter
    response = ssm_client.get_parameters(
        Names=parameter_names,
        WithDecryption=True  # This is required for SecureString parameters
    )

    # Extract the parameter value
    parameters = {param['Name']: param['Value'] for param in response['Parameters']}
    return parameters


def save_certificate(content: str):
    path = f"/tmp/{uuid.uuid4()}"
    with open(path, "w+") as f:
        f.write(content)

    os.chmod(path, 0o600)
    return path


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
                "database": db_name,
                "user": "yoda",
                "password": "admin",
                "host": "0.0.0.0",
                "port": 5432
            }

        elif env in ["dev", "prod"]:
            global CONFIG_CACHE
            if CONFIG_CACHE:
                configs = CONFIG_CACHE
            else:
                if not session:
                    session = boto3.Session()

                parameter_names = [
                    f'/calensync-{env}/db',
                    f'/calensync-{env}/root.crt',
                    f'/calensync-{env}/client.crt',
                    f'/calensync-{env}/client.key'
                ]
                parameters = get_multiple_parameters(parameter_names, session)

                configs = json.loads(parameters[parameter_names[0]])
                configs['sslmode'] = 'verify-ca'
                configs['sslrootcert'] = save_certificate(parameters[parameter_names[1]])
                configs['sslcert'] = save_certificate(parameters[parameter_names[2]])
                configs['sslkey'] = save_certificate(parameters[parameter_names[3]])
                CONFIG_CACHE = configs
        else:
            raise RuntimeError(f"Invalid environment {env}")

        db.init(
            **configs
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
