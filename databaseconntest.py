import pymysql
import os
from dotenv import load_dotenv

load_dotenv()
database_url = os.getenv("DATABASE_URL")
print(os.getenv("DATABASE_URL"))

# Parse the DATABASE_URL
import urllib.parse
url = urllib.parse.urlparse(database_url)
db_user = url.username
db_password = url.password
db_host = url.hostname
db_name = url.path[1:]  # Remove the leading slash

try:
    connection = pymysql.connect(host=db_host,
                                 user=db_user,
                                 password=db_password,
                                 database=db_name)
    print("Connection successful!")
    connection.close()
except pymysql.Error as e:
    print(f"Error connecting to MySQL: {e}")

