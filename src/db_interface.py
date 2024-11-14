import os
from dotenv import load_dotenv
import psycopg2
from psycopg2 import OperationalError


def create_connection():
    load_dotenv()
    try:
        connection = psycopg2.connect(
            dbname="sidb",
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            host=os.getenv("DB_HOST"),
            port="5432"
        )
        print("Connection to PostgreSQL database successful")
        return connection
    except OperationalError as e:
        print(f"Error: {e}")
        return None


def execute_query(db, query, params=None):
    try:
        cursor = db.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()
        return results
    except Exception as e:
        print(f"Database query failed: {e}")
        raise e
