import sqlite3

def get_db_connection():
    """Establishes a connection to the job_applications.db database."""
    conn = sqlite3.connect('job_applications.db')
    conn.row_factory = sqlite3.Row
    return conn