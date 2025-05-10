import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, inspect

load_dotenv()

db_url = os.getenv("DATABASE_URL")

def test_db_connection(db_url):
    engine=create_engine(db_url)
    inspector = inspect(engine)
    if inspector.has_schema("webapp_schema"):
        print("schema exists")
    else:
        print("schema DNE")
    
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1 FROM webapp_schema.users"))
            print("connected success")
            return True
    except Exception as e:
        print("failed")
        return False

if __name__ == "__main__":
    if db_url:
        print(f"testing connection string:{db_url} ")
        test_db_connection(db_url)
    else:
        print("URL not found")
