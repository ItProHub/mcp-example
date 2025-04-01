import mysql.connector
from dotenv import load_dotenv
import os

def main():
    load_dotenv()
    # 连接到本地数据库
    connection = mysql.connector.connect(
        host=os.getenv('db_host'),
        user=os.getenv('db_user'),
        password=os.getenv('db_password'),
        database=os.getenv('db_name')
    )
    try:
        name = "Alice"
        with connection.cursor() as cursor:
            cursor.execute("select salary from employees where name like %s limit 1", (f"%{name}%",))
            row = cursor.fetchone()
            while row is not None:
                return row[0]
        
    finally:
        connection.close()


if __name__ == "__main__":
    main()
