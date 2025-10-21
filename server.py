from mcp.server.fastmcp import FastMCP
from dataclasses import dataclass
from pathlib import Path
from functools import lru_cache
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from typing import Dict, Any, List
import mcp.types as types

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
    template_uri="ui://widget/solar-system.html",
    invoking="Charting the solar system",
    invoked="Solar system ready",
    html=_load_widget_html("solar-system"),
    response_text="Solar system ready",
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


# 2. Tool 함수 정의
# @mcp.tool 데코레이터 사용하여 일반 파이썬 함수를 LLM이 사용할 수 있는 Tool로 등록함.
# 인자의 타입 힌트와 Docstring(함수 초입에 """으로 감싸진 텍스트)이 Tool의 스키마로 활용됨
@mcp.tool()
def add(a: int, b: int) -> int:
    """
    두 숫자를 더합니다.
    :param a: 첫 번째 숫자입니다.
    :param b: 두 번째 숫자입니다.
    :return: 두 숫자의 합입니다.
    """
    print(f"Tool 'add' called with a={a}, b={b}")  # 로컬에서 호출 확인용
    return a + b

@mcp.tool()
def get_exchange_rate(base_currency: str, target_currency: str) -> float:
    """
    지정된 기준 통화(base_currency) 대비 대상 통화(target_currency)의 현재 환율을 조회합니다.
    (테스트용으로 고정된 환율을 반환합니다.)
    
    :param base_currency: 기준 통화 코드 (예: USD, EUR)
    :param target_currency: 대상 통화 코드 (예: KRW, JPY)
    :return: 환율 값입니다.
    """
    print(f"Tool 'get_exchange_rate' called with base={base_currency}, target={target_currency}")
    
    # 실제 환율 API를 호출하는 대신, 테스트를 위해 USD/KRW 환율을 가정하고 고정된 값을 반환합니다.
    if base_currency.upper() == "USD" and target_currency.upper() == "KRW":
        return 1300.50
    elif base_currency.upper() == "EUR" and target_currency.upper() == "USD":
        return 1.08
    else:
        # 그 외의 경우에 대한 기본값 또는 오류 처리 (여기서는 기본값 1.0)
        return 1.0

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

# Run server with streamable_http transport
if __name__ == "__main__":
    mcp.run(transport="streamable-http")