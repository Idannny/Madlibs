import pymysql

try:
    conn = pymysql.connect(
        host='localhost',
        user='flask_user',
        password='password',
        database='mad_app'
    )
    print("Successfully connected!")
    conn.close()
except Exception as e:
    print(f"Connection failed: {e}")
