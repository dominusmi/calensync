import os

from calensync.database.utils import DatabaseSession, reset_db

if __name__ == "__main__":
    env = "local"
    os.environ["AWS_PROFILE"] = "opali"
    if env == "prod":
        if input("CAREFUL: this is prod environment. Are you sure? [y/n]").strip() != "y":
            exit(0)

    with DatabaseSession(env) as db:
        reset_db()
