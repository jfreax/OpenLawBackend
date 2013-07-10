from contextlib import closing
import sqlite3
import codecs

DATABASE = 'openlaw.db'


def connect_db():
    return sqlite3.connect(DATABASE)

def init_db():
    with closing(connect_db()) as db:
        with codecs.open("schema.sql", 'r', 'utf-8') as f:
            db.cursor().executescript(f.read())
        db.commit()

