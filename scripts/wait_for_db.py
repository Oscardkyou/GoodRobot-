#!/usr/bin/env python3
import os
import sys
import time

import psycopg2

HOST = os.getenv("POSTGRES_HOST", "localhost")
PORT = int(os.getenv("POSTGRES_PORT", "5432"))
DB   = os.getenv("POSTGRES_DB", "masterbot")
USER = os.getenv("POSTGRES_USER", "masterbot")
PASS = os.getenv("POSTGRES_PASSWORD", "masterbot")
TIMEOUT = int(os.getenv("DB_WAIT_TIMEOUT", "60"))

start = time.time()
last_err = None
while True:
    try:
        conn = psycopg2.connect(host=HOST, port=PORT, dbname=DB, user=USER, password=PASS)
        conn.close()
        print("Database is ready")
        sys.exit(0)
    except Exception as e:
        last_err = e
        if time.time() - start > TIMEOUT:
            print(f"Database wait timeout after {TIMEOUT}s: {e}", file=sys.stderr)
            sys.exit(1)
        print("Waiting for database...", str(e))
        time.sleep(1)
