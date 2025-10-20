from mcp.server.fastmcp import FastMCP

# 1. FastMCP 서버 인스턴스 생성
# 이 인스턴스가 Tools를 관리하고 서버 역할을 수행한다.
mcp = FastMCP("Minimal HTTP Tool Server", host="0.0.0.0", port=8000)


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