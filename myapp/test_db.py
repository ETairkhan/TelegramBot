# test_db.py
from dotenv import load_dotenv
import psycopg2
import os

load_dotenv()

try:
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    print("Connected OK!")
except Exception as e:
    print("ERROR:", e)
