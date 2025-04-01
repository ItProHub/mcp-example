import mysql.connector
import requests
import os
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# 创建 MCP 服务器实例
mcp = FastMCP("DbDataService")

# 定义工具：从本地 MySQL 数据库获取数据
@mcp.tool()
def get_db_data(name: str) -> str:
    """Query salary of the person from a local MySQL database by his name."""
    load_dotenv()
    # 连接到本地数据库
    connection = mysql.connector.connect(
        host=os.getenv('db_host'),
        user=os.getenv('db_user'),
        password=os.getenv('db_password'),
        database=os.getenv('db_name')
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute("select salary from employees where name like %s limit 1", (f"%{name}%",))
            row = cursor.fetchone()
            while row is not None:
                return row[0]
        return ''
    finally:
        connection.close()

# 运行 MCP 服务器
if __name__ == "__main__":
    mcp.run()
