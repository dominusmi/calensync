from calensync.database.model import User, Calendar
from calensync.database.utils import DatabaseSession, reset_db

if __name__ == "__main__":
    with DatabaseSession("local"):
        reset_db()
