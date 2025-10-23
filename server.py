from mcp.server.fastmcp import FastMCP
import mcp.types as types
from pathlib import Path
from typing import Dict, Any, List

mcp = FastMCP("Test GPT App", host="0.0.0.0", port=8000)

# 예시를 위해 간단한 HTML 생성
HTML_TO_RENDER_TOOL_RESULT = """
<div>
    <h1>Test Tool Result</h1>
    <p>test tool 호출 결과를 표시하기 위한 UI 템플릿</p>
    <p>이 템플릿에 tool 호출 결과가 전달됨</p>
</div>
"""
# 1. UI 역할을 하는 Resource 등록
# - uri값이 이 리소스를 식별하는 ID값으로 사용됨. -> 유니크한 값으로 설정 필요 
# - mimeType을 'text/html+skybridge'으로 설정해야함. 그리고 text 필드에 렌더링될 html을 명시.
@mcp._mcp_server.list_resources()
async def _list_resources() -> List[types.Resource]:
    return [
        types.Resource(
            name="test widget", 
            title="test widget", 
            uri="ui://widget/test-widget.html",
            description="test widget",
            text=HTML_TO_RENDER_TOOL_RESULT,
            mimeType='text/html+skybridge',

        )
    ]

# 2. Tool 등록
# Tool과 UI역할을 하는 리소스를 연결하기 위해서 _meta필드의 openai/outputTemplate 필드에 UI 역할을 하는 리소스의 uri를 명시해야함.
# 여기서는 위에서 test widget 등록 시 사용한 uri 값을 전달
@mcp._mcp_server.list_tools()
async def _list_tools() -> List[types.Tool]:
    return [
        types.Tool(
            name="test-tool",
            title="test tool",
            description="test tool",
            inputSchema={},
            _meta={"openai/outputTemplate": "ui://widget/test-widget.html"},
        )
    ]


# Run server with streamable_http transport
if __name__ == "__main__":
    mcp.run(transport="streamable-http")


