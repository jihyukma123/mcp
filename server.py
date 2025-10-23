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
# 여기서 위에서 등록한 test widget의 uri 값을 전달
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

# 3. 앱 등록 시 list_tool() 호출의 결과에 따라 tool 별로 연결된 resource를 read하는 요청(ReadResourcesList)를 처리하는 함수 구현
async def _handle_read_resource(req: types.ReadResourceRequest) -> types.ServerResult:
    # 예제코드는 tool이 하나라서 바로 연결된 resource를 반환(실제 구현 시 요청받은 resource_uri 값이 따라 다른 resource를 반환하도록 구현되어야 함)
    return types.ServerResult(types.ReadResourceResult(contents=[
        types.TextResourceContents(
            uri="ui://widget/test-widget.html",
            mimeType='text/html+skybridge',
            text=HTML_TO_RENDER_TOOL_RESULT,
        )
    ]))

# 4. 도구 호출을 처리하는 함수 구현
# - structuredContent 필드값이 UI 렌더링에 사용됨
async def _call_tool_request(req: types.CallToolRequest) -> types.ServerResult:
    return types.ServerResult(types.CallToolResult(
        content = [
            types.TextContent(
                type="text",
                text="test tool 호출 결과",
            )
        ],
        structuredContent={},
    ))

mcp._mcp_server.request_handlers[types.ReadResourceRequest] = _handle_read_resource
mcp._mcp_server.request_handlers[types.CallToolRequest] = _call_tool_request

# 서버 실행
if __name__ == "__main__":
    mcp.run(transport="streamable-http")


