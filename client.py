import asyncio
import logging
from ollama import AsyncClient
from contextlib import AsyncExitStack
import json
from server import Server

class MCPClient:
    def __init__(self):
        self.servers = []
        self.tools = []
        self.exit_stack = AsyncExitStack()
        self.ollama = AsyncClient('127.0.0.1')

    async def initialize(self):
        server_config = None
        with open("servers_config.json", "r") as f:
            server_config = json.load(f)

        self.servers = [
            Server(name, srv_config)
            for name, srv_config in server_config["mcpServers"].items()
        ]

        for server in self.servers:
            try:
                await server.initialize()
            except Exception as e:
                logging.error(f"Failed to initialize server: {e}")
                await self.cleanup_servers()
                return
            
        for server in self.servers:
            tools = await server.list_tools()
            self.tools.extend(tools)        

        # 列出服务器提供的工具
        print("可用的工具:", self.tools)

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")
        
        while True:
            try:
                query = input("\nQuery: ").strip()
                
                if query.lower() == 'quit':
                    break
                    
                response = await self.process_query(query)
                print("\n" + response)
                    
            except Exception as e:
                print(f"\nError: {str(e)}")


    async def process_query(self, query: str) -> str:
        """Process a query using Claude and available tools"""

        tools_description = "\n".join([tool.format_for_llm() for tool in self.tools])

        system_message = (
                "You are a helpful assistant with access to these tools:\n\n"
                f"{tools_description}\n"
                "Choose the appropriate tool based on the user's question. "
                "If no tool is needed, reply directly.\n\n"
                "IMPORTANT: When you need to use a tool, you must ONLY respond with "
                "the exact JSON object format below, nothing else:\n"
                "{\n"
                '    "tool": "tool-name",\n'
                '    "arguments": {\n'
                '        "argument-name": "value"\n'
                "    }\n"
                "}\n\n"
                "After receiving a tool's response:\n"
                "1. Transform the raw data into a natural, conversational response\n"
                "2. Keep responses concise but informative\n"
                "3. Focus on the most relevant information\n"
                "4. Use appropriate context from the user's question\n"
                "5. Avoid simply repeating the raw data\n\n"
                "Please use only the tools that are explicitly defined above."
            )

        messages = [{"role": "system", "content": system_message}]
        
        messages.append({"role": "user", "content": query})

        llm_response = await self.ollama.chat(
            'qwen2.5:0.5b',        
            messages=messages
        )
        logging.info("\nAssistant: %s", llm_response)

        llm_response = llm_response.message['content']

        result = await self.process_llm_response(llm_response)

        if result != llm_response:
            messages.append({"role": "assistant", "content": llm_response})
            messages.append({"role": "system", "content": result})

            final_response = await self.ollama.chat(
                'qwen2.5:0.5b',        
                messages=messages
            )
            final_response = final_response.message['content']
            logging.info("\nFinal response: %s", final_response)
            messages.append(
                {"role": "assistant", "content": final_response}
            )
        else:
            messages.append({"role": "assistant", "content": llm_response})


        return final_response
    


    async def process_llm_response(self, llm_response: str) -> str:
        """Process the LLM response and execute tools if needed.

        Args:
            llm_response: The response from the LLM.

        Returns:
            The result of tool execution or the original response.
        """
        import json

        try:
            tool_call = json.loads(llm_response)
            if "tool" in tool_call and "arguments" in tool_call:
                logging.info(f"Executing tool: {tool_call['tool']}")
                logging.info(f"With arguments: {tool_call['arguments']}")

                for server in self.servers:
                    tools = await server.list_tools()
                    if any(tool.name == tool_call["tool"] for tool in tools):
                        try:
                            result = await server.execute_tool(
                                tool_call["tool"], tool_call["arguments"]
                            )

                            if isinstance(result, dict) and "progress" in result:
                                progress = result["progress"]
                                total = result["total"]
                                percentage = (progress / total) * 100
                                logging.info(
                                    f"Progress: {progress}/{total} "
                                    f"({percentage:.1f}%)"
                                )

                            return f"Tool execution result: {result}"
                        except Exception as e:
                            error_msg = f"Error executing tool: {str(e)}"
                            logging.error(error_msg)
                            return error_msg

                return f"No server found with tool: {tool_call['tool']}"
            return llm_response
        except json.JSONDecodeError:
            return llm_response
        

    
    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()


async def main():
    client = MCPClient()
    try:
        await client.initialize()
        await client.chat_loop()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
