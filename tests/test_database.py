from sqlalchemy import text
from database.session import engine

def test_database_connection():
    with engine.connect() as connection: