import mysql.connector
import requests
import os
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# 创建 MCP 服务器实例
mcp = FastMCP("WebDataService")

# 定义工具：从网络上搜索数据
@mcp.tool()
def get_web_data(query: str) -> str:
    """Search the web for current information on a topic"""
    load_dotenv()
    api_key = os.getenv('SEARCH_API_KEY')

    if not api_key:
        return {"error": "API key not found in environment variables"}

    url = "https://www.searchapi.io/api/v1/search"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    params = {
        "engine": "google_news",
        "q": query,
        "num": 5
    }

    try:
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 401:
            return "error: Invalid API key or authentication failed"
        elif response.status_code == 429:
            return "error: Rate limit exceeded"

        response.raise_for_status()

        content = []
        search_results = response.json()
        for result in search_results["organic_results"][:4]:  # Taking the top 4 results
            if "snippet" in result:
                content.append(result["snippet"])

        return "\n\n".join(content)   

    except requests.exceptions.RequestException as e:
        error_msg = f"Error fetching search results: {e}"
        if hasattr(e, 'response') and e.response:
            try:
                error_details = e.response.json()
                error_msg = f"{error_msg} - {error_details.get('message', '')}"
            except:
                pass
        return error_msg

# 运行 MCP 服务器
if __name__ == "__main__":
    mcp.run()
