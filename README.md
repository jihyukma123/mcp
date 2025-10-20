# mcp 서버 만들기

공식 python-sdk를 써서 개발함

# ngrok으로 배포하기

ngrok을 로컬에 설치해서 배포해서 테스트 함

curl -X POST https://unvocable-lajuana-preapply.ng \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "id": 1
  }'


curl -X POST https://unvocable-lajuana-preapply.ngrok-free.dev/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "id": 1
  }'

  ➜  ~ curl -X POST https://unvocable-lajuana-preapply.ngrok-free.dev/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {},
      "clientInfo": {
        "name": "test-client",
        "version": "1.0.0"
      }
    },
    "id": 1
  }'
event: message
data: {"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2024-11-05","capabilities":{"experimental":{},"prompts":{"listChanged":false},"resources":{"subscribe":false,"listChanged":false},"tools":{"listChanged":false}},"serverInfo":{"name":"Minimal HTTP Tool Server","version":"1.17.0"}}}