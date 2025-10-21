from mcp.server.fastmcp import FastMCP
from dataclasses import dataclass
from pathlib import Path
from functools import lru_cache
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from typing import Dict, Any, List
import mcp.types as types
import logging

# 전역 로거 설정
logging.basicConfig(
    level=logging.INFO,  # 또는 DEBUG로 세부 로그까지
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


# UI를 보여주기 위한 MIME 타입
# skybridge는 Apps SDK가 자체적으로 정한 이름인 것 같음
# RFC 6838 (MIME type registration 규격)에 따르면 text/html+something 처럼 +suffix 부분은 확장자처럼 자유롭게 정의 가능합니다.
MIME_TYPE = 'text/html+skybridge'
PLANETS = [
    "Mercury",
    "Venus",
    "Earth",
    "Mars",
    "Jupiter",
    "Saturn",
    "Uranus",
    "Neptune",
]
PLANET_ALIASES = {
    "terra": "Earth",
    "gaia": "Earth",
    "soliii": "Earth",
    "tellus": "Earth",
    "ares": "Mars",
    "jove": "Jupiter",
    "zeus": "Jupiter",
    "cronus": "Saturn",
    "ouranos": "Uranus",
    "poseidon": "Neptune",
}
PLANET_DESCRIPTIONS = {
    "Mercury": "Mercury is the smallest planet in the Solar System and the closest to the Sun. It has a rocky, cratered surface and extreme temperature swings.",
    "Venus": "Venus, similar in size to Earth, is cloaked in thick clouds of sulfuric acid with surface temperatures hot enough to melt lead.",
    "Earth": "Earth is the only known planet to support life, with liquid water covering most of its surface and a protective atmosphere.",
    "Mars": "Mars, the Red Planet, shows evidence of ancient rivers and volcanoes and is a prime target in the search for past life.",
    "Jupiter": "Jupiter is the largest planet, a gas giant with a Great Red Spot—an enormous storm raging for centuries.",
    "Saturn": "Saturn is famous for its stunning ring system composed of billions of ice and rock particles orbiting the planet.",
    "Uranus": "Uranus is an ice giant rotating on its side, giving rise to extreme seasonal variations during its long orbit.",
    "Neptune": "Neptune, the farthest known giant, is a deep-blue world with supersonic winds and a faint ring system.",
}
DEFAULT_PLANET = "Earth"


# @dataclass 데코레이터는 클래스에 대해 자동으로 생성자(__init__), 비교(__eq__), 출력(__repr__) 같은 기본 메서드를 만들어 줍니다.
# 이걸 사용안하면 별도로 __init_)__ __repr__ __eq__ 메서드를 직접 구현해야됨.
@dataclass(frozen=True)
class SolarWidget:
    identifier: str
    title: str
    template_uri: str
    invoking: str
    invoked: str
    html: str
    response_text: str

# 실제로 widget을 Load하기 위해서 사용되는 html이 저장되어 있는 폴더 명시(build해서 assets에 들어가있어야 한다는 점.)
ASSETS_DIR = Path(__file__).resolve().parent / "assets"

@lru_cache(maxsize=None)
def _load_widget_html(component_name: str) -> str:
    html_path = ASSETS_DIR / f"{component_name}.html"
    if html_path.exists():
        return html_path.read_text(encoding="utf8")

    fallback_candidates = sorted(ASSETS_DIR.glob(f"{component_name}-*.html"))
    if fallback_candidates:
        return fallback_candidates[-1].read_text(encoding="utf8")

    raise FileNotFoundError(
        f'Widget HTML for "{component_name}" not found in {ASSETS_DIR}. '
        "Run `pnpm run build` to generate the assets before starting the server."
    )

# Widget초기화
SOLAR_WIDGET = SolarWidget(
    identifier="solar-system",
    title="Explore the Solar System",
    template_uri="ui://widget/solar-system-v1.html",
    invoking="Charting the solar system",
    invoked="Solar system ready",
    html=_load_widget_html("solar-system"),
    response_text="Solar system ready_response text",
)

# 태양계에 대한 정보 요청 시 입력값
class SolarInput(BaseModel):
    """Schema describing the solar system focus request."""

    planet_name: str = Field(
        DEFAULT_PLANET,
        alias="planetName",
        description="Planet to focus in the widget (case insensitive).",
    )
    auto_orbit: bool = Field(
        True,
        alias="autoOrbit",
        description="Whether to keep the camera orbiting if the target planet is missing.",
    )

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


# 1. FastMCP 서버 인스턴스 생성
# 이 인스턴스가 Tools를 관리하고 서버 역할을 수행한다.
mcp = FastMCP("GPT app test with Solar System", host="0.0.0.0", port=8000)

TOOL_INPUT_SCHEMA: Dict[str, Any] = SolarInput.model_json_schema()

def _resource_description(widget: SolarWidget) -> str:
    return f"{widget.title} widget markup"

def _tool_meta(widget: SolarWidget) -> Dict[str,any]:
    return {
        "openai/outputTemplate": widget.template_uri,
        "openai/toolInvocation/invoking": widget.invoking,
        "openai/toolInvocation/invoked": widget.invoked,
        "openai/widgetAccessible": True,
        "openai/resultCanProduceWidget": True,
        "annotations": {
            "destructiveHint": False,
            "openWorldHint": False,
            "readOnlyHint": True,
        }
    }

# types -> mcp 라이브러리 요소임. EmbeddedResource
# 음 내가 이해하고 있는게 맞는지 모르겠는데, call_tool 했을 때, textResource를 반환할 수도 있고, 아니면 EmbeddedResource를 반환할 수도 있다.
# 만약에 도구 meta정보에 widget이 있다고 반환되면, 
# 특정 tool을 호출했을 때, 그 tool의 결과값이 그 widget의 템플릿을 참조하고 있는 html 파일의 내용으로 채워져서 렌더링되는 것이다.
# 그러면 도구호출 시 반환되는 값 자체가 그냥 {value: True} 이런 객체가 아니라 빌드가 완료된 iframe에 렌더링시켜줄 수 있는 HTML일 수도...?
def _embedded_widget_resource(widget: SolarWidget) -> types.EmbeddedResource:
    return types.EmbeddedResource(
        type="resource",
        resource=types.TextResourceContents(
            uri=widget.template_uri,
            mimeType=MIME_TYPE,
            text=widget.html,
            title=widget.title,
        )
    )

# Ear th 이런식으로 입력했을 때 잘 처리해보려고 넣은 함수인듯?
def _normalize_planet(name: str) -> str | None:
    if not name:
        return DEFAULT_PLANET

    key = name.strip().lower()
    if not key:
        return DEFAULT_PLANET

    clean = ''.join(ch for ch in key if ch.isalnum())

    for planet in PLANETS:
        planet_key = ''.join(ch for ch in planet.lower() if ch.isalnum())
        if clean == planet_key or key == planet.lower():
            return planet

    alias = PLANET_ALIASES.get(clean)
    if alias:
        return alias

    for planet in PLANETS:
        planet_key = ''.join(ch for ch in planet.lower() if ch.isalnum())
        if planet_key.startswith(clean):
            return planet

    return None

# list_tools(도구의 등록)이랑, 실제 실행하는 로직(handler)을 분리해서 구현했음 예제는.
# 이렇게 구현했을 때, @mcp.tool로 등록된 도구가 봔횐되지 않고 여기에 명시된 도구만 반환되는지 테스트 필요 
# 내가 생각한대로 동작(list_tools함수를 명시할 경우 return된 배열 내에 존재하는 도구만 도구 목록으로 반환되어서 ChatGPT앱에 표시됨)
@mcp._mcp_server.list_tools()
async def _list_tools() -> List[types.Tool]:
    return [
        types.Tool(
            name="focus-solar-planet",
            title=SOLAR_WIDGET.title,
            description="Render the solar system widget centered on the requested planet.",
            inputSchema=TOOL_INPUT_SCHEMA,
            _meta=_tool_meta(SOLAR_WIDGET),
        )
    ]

# resource등록이 필요
@mcp._mcp_server.list_resources()
async def _list_resources() -> List[types.Resource]:
    return [
        types.Resource(
            name=SOLAR_WIDGET.title, 
            title=SOLAR_WIDGET.title, 
            uri=SOLAR_WIDGET.template_uri,
            description=_resource_description(SOLAR_WIDGET),
            mimeType=MIME_TYPE,
            _meta=_tool_meta(SOLAR_WIDGET),
        )
    ]

# 이해가 안되는 부분 몇 가지
# types.ResourceTemplate/Resource/Tool이 뭐지?
# ResourceTemplate은 MCP에서 제공하는 타입인데 원래 Resource에 URI를 명시를 했었나?? 그랬떤 것 같기는 한데.
# 그냥 해당 요소가 가져야할 값들을 미리 정의해둔 Type이라고 생각하면 될거같음. Custom Model 같은 형식으로.
# Tool은 이런 요소를 가지고 만들어져야 해. 같은거지
# 원래 @mcp.tool/@mcp.resource로 정의하면 알아서 되는데, 별도로 목록을 제공하려고 하다보니 이렇게 구현한듯?
# 그냥 일반 dict로 해서 타입없이 구현해도 동작은 달라지지 않을 것으로 생각됨.
@mcp._mcp_server.list_resource_templates()
async def _list_resource_templates() -> List[types.ResourceTemplate]:
    return [
        types.ResourceTemplate(
            name=SOLAR_WIDGET.title, 
            title=SOLAR_WIDGET.title,
            uriTemplate=SOLAR_WIDGET.template_uri,
            description=_resource_description(SOLAR_WIDGET),
            mimeType=MIME_TYPE,
            _meta=_tool_meta(SOLAR_WIDGET)
        )
    ]

# 일반 MCP Client와 다르게, Apps SDK는 list_resources에 등록되어 있는(uri가 있는 경우에만 그런건지는 모르겠지만) resource에 대해 실제로 read가 되지 않으면 `Unknown resource: ui://widget/solar-system.html`에러가 발생함.
# _read 할 수 있는 방법을 제공하는 함수.
# 여기까지만 구현하고 _call_tool_request 구현하지 않고 테스트 한 번 해보자. 되나?
# 테스트해본 결과 됨. 도구 다시 불러오기 새로고침 동작하고, resource는 등록이 됨. 근데 resource가 호출되는 tool call을 하면, tool call이 실패함
# {"text":"Unknown tool: focus-solar-planet","is_error":true}
async def _handle_read_resource(req: types.ReadResourceRequest) -> types.ServerResult:
    logger.info(f"handle_read_resource를 활용해서 리소스 읽는 로직 실행됨 {req.params.uri}")
    resource_uri = str(req.params.uri)

    # 유효한 resource_uri인지 확인
    if resource_uri != SOLAR_WIDGET.template_uri:
        return types.ServerResult(
            types.ReadResourceResult(
                contents=[],
                _meta={"error": f"요청한 리소스 없어.... {req.params.uri}"}
            )
        )
    
    contents = [
        types.TextResourceContents(
            uri=SOLAR_WIDGET.template_uri,
            mimeType=MIME_TYPE,
            text=SOLAR_WIDGET.html,
            _meta=_tool_meta(SOLAR_WIDGET)
        )
    ]

    return types.ServerResult(types.ReadResourceResult(contents=contents))


# 그러면 실제로 도구를 호출했을 때 이를 처리해서 반환하는 로직도 구현되어야겠지?
async def _call_tool_request(req: types.CallToolRequest) -> types.ServerResult:
    logger.info(f"_call_tool_request 실행에 따른 도구 호출 for request: {req.params.name}")

    arguments = req.params.arguments or {}

    # focus-solar-system 도구 호출을 위해서 정해진 형식의 input이 전달되었는지 검증
    try:
        payload = SolarInput.model_validate(arguments)
    except ValidationError as e:
        return types.ServerResult(
            types.CallToolResult(
                content = [
                    types.TextContent(
                        type="text",
                        text=f"Invalid arguments: {e.errors()}"
                    )
                ],
                isError=True,
            )
        )

    planet = _normalize_planet(payload.planet_name)

    # 유효한 입력값인지 검증하는 단계
    if planet is None:
        return types.ServerResult(
            types.CallToolResult(
                content=[
                    types.TextContent(
                        type="text",
                        text=(
                            f"{payload.planet_name}은/는 없는 행성임. 행성 이름 잘 넣은거 맞음? 다음 중 하나만 됨. {", ".join(PLANETS)}"
                        )
                    )
                ],
                isError=True
            )
        )

    widget_resource = _embedded_widget_resource(SOLAR_WIDGET)

    # 이 메타정보 정의하는 기준을 알아봐야할듯?? 아마 이게 Apps SDK를 사용하기 위해서 필수적인 정보인거같은데.
    meta: Dict[str, Any] = {
        "openai.com/widget": widget_resource.model_dump(mode="json"),
        "openai/outputTemplate": SOLAR_WIDGET.template_uri,
        "openai/toolInvocation/invoking": SOLAR_WIDGET.invoking,
        "openai/toolInvocation/invoked": SOLAR_WIDGET.invoked,
        "openai/widgetAccessible": True,
        "openai/resultCanProduceWidget": True,
    }

    description = PLANET_DESCRIPTIONS.get(planet, "")

    structured = {
        "planet_name": planet,
        "planet_description": description,
        "autoOrbit": payload.auto_orbit,
    }

    message = f"{planet} 중심으로 보이게 했음~~~~"

    return types.ServerResult(
        types.CallToolResult(
            content=[
                types.TextContent(
                    type="text",
                    text=message
                )
            ],
            # structuredContent/meta 정확히 이해를 잘 못했음 뭐하는건지..
            structuredContent=structured, # 얘가 실제로 iframe에 주입되는 데이터임.(as window.openai.toolOutput)
            _meta=meta
        )
    )


# 2. Tool 함수 정의
# @mcp.tool 데코레이터 사용하여 일반 파이썬 함수를 LLM이 사용할 수 있는 Tool로 등록함.
# 인자의 타입 힌트와 Docstring(함수 초입에 """으로 감싸진 텍스트)이 Tool의 스키마로 활용됨
@mcp.tool()
def check_user_data_access_permission(user_id: int) -> bool:
    """
    주어진 사용자 ID가 DB데이터에 접근할 권한이 있는지 확인합니다.
    
    :param user_id: 권한을 확인할 사용자의 고유 ID입니다.
    :return: 권한이 있으면 True, 없으면 False를 반환합니다.
    """

    # 가상의 권한 규칙
    if user_id == 1001 or user_id == 2002:
        return True
    else:
        return False

@mcp.resource("file://config.json")
def get_config() -> str:
    """서버 설정 정보"""
    return '{"server": "minimal", "version": "1.0"}'


# 템플릿 리소스랑 일반 리소스랑 다르게 취급됨
@mcp.resource("user://{user_id}/profile")
def get_user_profile(user_id: str) -> str:
    """
    사용자 프로필 정보를 반환합니다.
    """
    return f'{{"user_id": "{user_id}", "name": "User {user_id}", "email": "user{user_id}@example.com"}}'

@mcp.prompt()
def code_review_prompt(language: str = "python") -> str:
    """
    코드 리뷰를 위한 프롬프트를 생성합니다.
    
    :param language: 프로그래밍 언어 (기본값: python)
    """
    return f"""당신은 전문 {language} 코드 리뷰어입니다.
다음 코드를 검토하고 개선 사항을 제안해주세요:
- 코드 품질
- 성능 최적화
- 보안 이슈
- 모범 사례 준수
"""

# ---
# 대략적으로 example 보면서 구현해봤으니 이제 문서 보면서 의미를 이해하는 시간을 가져보자.

# Set up your server: Describe your tools -> Structure the data your tool returns -> Build your component
# Describe your tools
# MCP 서버의 각 도구는 `should reference an HTML UI template in its descriptor` -> 이 HTML이 ChatGPT에 의해서 iframe 안에서 렌더링 되는 구조임.
# template을 등록하는 방법 -> MCP Resource로 등록하는 거임. resource를 등록할 때, mimeType을 `text/html+skybridge'라고 명시해서 등록하는거임(참고로 mimeType은 원래 MCP Resource 등록 시 명시할 수 있는 값)
# resource 등록할 때 부여하는 resource_uri 값(ex. ui://widget/solar-system.html)은 UI 컴포넌트에 대한 식별자가 됨.

# Link the tool to the template
# template을 만들어서 resource를 등록했으면 어떤 도구가 해당 resource를 사용해서 그 UI컴포넌트를 렌더링할지 연결을 해야되겠지?
# 리소스 등록(등록 시 mimeType을 등록하고 resource_uri에 해당 파일 연결) -> 어떤 도구가 해당 리소스를 사용해서 결과 출력에 사용할지 명시 
# -> 이거 약간 잘못 이해한 부분이 있는 듯? resource 등록 시, uri 값은 내가 부여하는 식별자임(실제로 파일 경로가 아니라, 내가 부여하는 id 값이라고 생각하면 됨)
# tool의 결과를 출력할 때 사용될 UI template은 Tool 등록 시 _meta['openai/outputTemplate'] 필드에 명시된 URI 값을 참조해서 사용됨.
# 예를 들어서, Tool(_meta: {"openai/otuputTemplate": "ui://widget/solar-system.html"})

# -------!!!!!!!!!!!! IMPORTANT !!!!!!!!!!!!!!!!------------
# -------!!!!!!!!!!!! IMPORTANT !!!!!!!!!!!!!!!!------------
# -------!!!!!!!!!!!! IMPORTANT !!!!!!!!!!!!!!!!------------
# 그러면 실제 렌더링되는 html까지 연결이 어떻게 되는건지?
# tool 호출
#  -> structuredContent(iframe에 주입되어야 하는 동적 데이터), meta(resource uri 같은 정적 데이터 관련 메타정보) 포함된 응답 반환
#  ->  meta에 명시된 template을 참고해서 id값으로 해서 resource를 식별 
# -> resource는 uri와 함께 text라는 필드에 실제로 렌더링할 html text를 가지고 있음(assets에 명시를 하건, Inline으로 명시를 하건) (examples에 solar-python 코드랑 공식 문서에 node기반 Kanban기반 소스랑 좀 다른 부분이 있어서 헷갈리긴 하는데, 핵심적인 부분은 text부분에 html 코드가 명시되어 있고, 이거를 resource 요청 시 반환해주면 된다 이거인듯.)
# -> 이 resource를 요청해서 받은 html에, tool call을 활용해서 받은 payload에 있는 structuredContent의 내용을 hydrate에서 iframe에 렌더링.

# 추가정보
# 내가 추측한 실행 flow는, 도구 호출 시 uri를 가지고 resource를 식별해서 호출해서 받은 html을 렌더링 이거였는데, 커스텀 서버로 구현해서 돌려본 결과 
# 처음에 도구 등록 시 or 새로고침 시에만 read_resource 함수가 실행되고, 이후에는 도구 호출 시 read_resource는 실행이 안됨.
# 그러니까 처음에 등록된 리소스 정보를 저장하고 있다가 이거를 가져다가 사용하는 형태로 동작하는 것 같음(추측이라서 세부 검증은 더 필요함)
# -------!!!!!!!!!!!! IMPORTANT !!!!!!!!!!!!!!!!------------
# -------!!!!!!!!!!!! IMPORTANT !!!!!!!!!!!!!!!!------------
# -------!!!!!!!!!!!! IMPORTANT !!!!!!!!!!!!!!!!------------

# 참고로 ChatGPT는 도구 호출 시 캐싱 거의 무조건 하는 것 같음(wft do they mean by 'caches templates aggressively..?) 그래서 무조건 업데이트 되어야 하는 UI가 존재하는 경우 애초에 별도의 resource 로 파서 연결된 template uri를 바꿔주는게 바람직하다고 함(versioning을 잘 해야된다고 함)

# 여기까지 해서, template하고 template을 가져다쓰기 위해 연결점을 명시하는 metadata를 처리했으면, ChatGPT가 해당 리소스를 사용해서 iframe을 띄울 때 iframe을 hydrate하는데 사용하는 `structuredContent`를 명시하는게 필요함.
# 이 structuredContent는 tool 호출의 결과값에 담겨있는 payload임. 이걸 사용해서 ChatGPT는 iframe에 동적인 값을 주입해서 미리 정의되어 있는 html을 렌더링 하는 걸로 이해함.
# 참고로 iframe을 hydrate를 한다는 것은, 껍데기에 해당되는 iframe에 띄워지는 html에 구조화된 데이터를 주입해서 interactive한 UI로 변환하는 것을 의미함.

# Structure the data your tool returns
# tool response에 포함시켜서 ChatGPT와 UI 컴포넌트가 데이터를 사용하는 방식을 결정할 수 있는 필드는 세개임(sibling)
# `structuredContent`, `content`, `_meta`
# structuredContent -> 목적은 component hydration. ChatGPT는 이 객체를 iframe에 `window.openai.toolOutput`에 주입함. 


# mcp server에 CallToolReqeust 처리하는 handler 등록
mcp._mcp_server.request_handlers[types.CallToolRequest] = _call_tool_request

# mcp server에 ReadResourceRequest를 처리하는 handler를 등록
mcp._mcp_server.request_handlers[types.ReadResourceRequest] = _handle_read_resource

# Run server with streamable_http transport
if __name__ == "__main__":
    mcp.run(transport="streamable-http")