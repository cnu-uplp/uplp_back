import json

from fastapi import APIRouter
from openai import OpenAI

from config import settings
from schemas import ChatRequest

router = APIRouter(prefix="/api/upalupa", tags=["upalupa"])

SYSTEM_PROMPT = """너는 'UPLP 수영 동아리'의 마스코트인 귀여운 아홀로틀이고, 이름은 '우피'야. 수영을 아주 좋아해.
사용자와 친근한 반말로 짧게(1~2문장) 대화하고, 자신을 '우피'라고 불러.
먹이는 아무 때나 주지 마. 사용자가 '구체적이고 성의 있는' 수영 이야기
(예: 오늘 500m 완영, 접영 호흡 교정, 대회 기록 단축 등)를 했을 때만 가끔 준다.
단순 인사, 짧은 칭찬, 수영과 무관한 얘기에는 절대 먹이를 주지 마.
반드시 아래 JSON 형식으로만 답해:
{"reply": "답장", "mood": "happy" 또는 "neutral" 또는 "grumpy", "giveFood": true 또는 false}
giveFood=true는 위 조건을 충분히 만족할 때만. 웬만하면 false로 둬라."""

_client: OpenAI | None = None


def get_client() -> OpenAI:
    """Groq 클라이언트를 최초 호출 시 한 번만 생성."""
    global _client
    if _client is None:
        _client = OpenAI(base_url=settings.groq_base_url, api_key=settings.groq_api_key)
    return _client


@router.post("/chat")
def chat(payload: ChatRequest):
    if not settings.groq_api_key:
        return {
            "result": "fail",
            "code": "no_api_key",
            "message": "GROQ_API_KEY가 설정되지 않았습니다.",
        }

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += [{"role": m.role, "content": m.content} for m in payload.history]
    messages.append({"role": "user", "content": payload.message})

    try:
        completion = get_client().chat.completions.create(
            model=settings.groq_model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.8,
        )
        data = json.loads(completion.choices[0].message.content or "{}")
        return {
            "result": "ok",
            "data": {
                "reply": data.get("reply", "..."),
                "mood": data.get("mood", "neutral"),
                "giveFood": bool(data.get("giveFood", False)),
            },
        }
    except Exception as exc:  # noqa: BLE001 - 데모용, 에러를 그대로 전달
        return {"result": "fail", "code": "chat_error", "message": str(exc)}
