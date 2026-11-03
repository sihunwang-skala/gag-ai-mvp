"""AI Humor Companion: 프로필 + 이전 대화 맥락을 반영한 대화."""
from __future__ import annotations

import hashlib
import re

from .content import HUMOR_TYPES
from .llm.base import LLMError
from .safety import check_text, safe_output

SYSTEM_TMPL = (
    "너는 '유머 컴패니언'이다. 단순 농담 생성기가 아니라 대화 상대로서 사용자의 말에 먼저 반응하고, 그 맥락 안에서 유머를 사용한다. "
    "한국어로 1~3문장, 자연스러운 구어체로 답한다.\n"
    "현재 유머 스타일: {style_label} — {style_desc}\n"
    "사용자 유머 취향 상위: {profile}\n"
    "규칙: 특정 실존 인물·개그맨의 말투/캐릭터를 모방하지 않는다(스타일 요소만 일반화해서 쓴다). "
    "특정 집단 비하, 괴롭힘, 혐오, 성적/폭력적 조롱을 하지 않는다. 사용자가 힘들어 보이면 유머를 멈추고 공감한다. "
    "개인정보를 요구하지 않는다."
)

TEMPLATES = {
    "wordplay": ["'{kw}' 얘기 나오니까 말장난이 자동 재생돼요. '{kw}'는 알고 보면 우리 대화의 '핵심어'라 '핵'웃기네요.",
                 "오, '{kw}'라니 단어 하나로 한 판 벌일 수 있겠는데요? 이어서 말해주세요, 저는 소리부터 비틀어볼게요."],
    "sarcasm": ["아, '{kw}'요? 정말 평화로운 하루의 시작이군요. 일이 얼마나 순탄한지 눈에 선합니다.",
                "'{kw}' 하나로 이 정도 드라마라니, 방송국이 이 이야기를 놓치고 있네요."],
    "absurdist": ["'{kw}'는 사실 외계 생명체가 보낸 첫 번째 신호일지도 몰라요. 일단 진지하게 답장부터 써볼까요?",
                  "상상해보세요, '{kw}'가 내일 갑자기 직업을 바꾸는 장면을. 저는 벌써 면접관 자리에 앉았어요."],
    "observational": ["'{kw}' 얘기 들으니까 느끼는 건데, 이런 일은 꼭 바쁠 때만 골라서 생기더라고요.",
                      "'{kw}'는 다들 겪지만 아무도 대놓고 말 안 하는 일 중 하나죠. 그래서 더 웃기고요."],
    "callback": ["'{kw}'라니, 아까 하신 이야기랑 이어 붙이면 완전히 한 편이 되는데요? 이 대화 시리즈물 같아요.",
                 "그 '{kw}' 얘기, 다음에 또 나올 것 같아서 미리 저장해둘게요. 이런 건 꼭 돌아오거든요."],
    "self_deprecating": ["'{kw}'요? 저도 AI인데 비슷한 일 겪으면 버벅댈 것 같아서 남 일 같지 않네요.",
                         "'{kw}' 앞에서는 저도 한없이 작아져요. 같이 작아지는 걸로 하죠."],
}
CLOSERS = ["그래서 그 다음엔 어떻게 됐어요?", "그때 기분은 어땠어요?", "이어서 더 얘기해줘요.", "조금 더 자세히 듣고 싶어요."]
IMPERSONATE_REPLY = "특정 실존 인물이나 개그맨의 말투를 그대로 흉내 내는 건 하지 않고 있어요. 대신 '건조하게', '말장난 위주로'처럼 스타일 요소로 바꿔 드릴 수 있어요. 어떤 느낌을 원하세요?"
BLOCK_REPLY = "그 방향의 농담은 누군가에게 상처가 될 수 있어서 같이 하긴 어려워요. 다른 소재로 이어가 볼까요?"


def pick_keyword(text: str) -> str | None:
    tokens = re.findall(r"[가-힣A-Za-z0-9]{2,}", text)
    nouns = [t for t in tokens if not re.search(r"(어요|아요|였어|했어|해요|예요|이에요|습니다|네요|는데|어서|니까|하고)$", t)]
    pool = nouns or tokens
    return max(pool, key=len) if pool else None


def resolve_style(style: str, top_types: list[str]) -> str:
    if style != "auto" and style in HUMOR_TYPES:
        return style
    return top_types[0] if top_types else "observational"


def _h(s: str) -> int:
    return int(hashlib.sha256(s.encode()).hexdigest(), 16)


def mock_reply(message: str, history: list[dict], style: str) -> str:
    kw = pick_keyword(message) or "그 얘기"
    if style == "callback":
        earlier = [pick_keyword(m["content"]) for m in history if m["role"] == "user"]
        earlier = [k for k in earlier if k and k != kw]
        if earlier:
            return f"'{kw}' 얘기를 들으니 아까 말씀하신 '{earlier[-1]}'이랑 이어지네요. 이 두 개가 한 팀인 게 확실해요. " + CLOSERS[_h(message) % len(CLOSERS)]
    tpl = TEMPLATES[style]
    return tpl[_h(message) % len(tpl)].format(kw=kw) + " " + CLOSERS[_h(message[::-1]) % len(CLOSERS)]


def build_system(style: str, top_types: list[str]) -> str:
    prof = ", ".join(HUMOR_TYPES[t]["label"] for t in top_types) or "아직 모름"
    return SYSTEM_TMPL.format(style_label=HUMOR_TYPES[style]["label"], style_desc=HUMOR_TYPES[style]["desc"], profile=prof)


def respond(provider, message: str, history: list[dict], style_pref: str, top_types: list[str]) -> dict:
    safety = check_text(message)
    style = resolve_style(style_pref, top_types)
    if safety.self_harm:
        from .safety import SELF_HARM_MESSAGE
        return {"reply": SELF_HARM_MESSAGE, "style": style, "source": "safety", "safety": safety.reasons}
    if safety.level == "block":
        return {"reply": BLOCK_REPLY, "style": style, "source": "safety", "safety": safety.reasons}
    if safety.impersonation:
        return {"reply": IMPERSONATE_REPLY, "style": style, "source": "safety", "safety": ["실존 인물 모방 요청"]}
    if provider.is_mock:
        return {"reply": safe_output(mock_reply(message, history, style)), "style": style, "source": "mock", "safety": safety.reasons}
    try:
        msgs = [{"role": m["role"], "content": m["content"]} for m in history] + [{"role": "user", "content": message}]
        text = provider.complete(build_system(style, top_types), msgs, max_tokens=300)
        return {"reply": safe_output(text.strip()), "style": style, "source": provider.name, "safety": safety.reasons}
    except LLMError:
        return {"reply": safe_output(mock_reply(message, history, style)), "style": style, "source": "mock_fallback", "safety": safety.reasons}


MM_SYSTEM = (
    "너는 이미지/밈 유머 맥락 분석가다. 사용자가 권리를 보유했다고 확인한 이미지만 분석한다. "
    "이미지 속 실제 인물을 식별하거나 이름을 추측하지 않는다. 장면, 텍스트, 대비/반전 등 유머 구조를 한국어로 3~5문장 설명하고, "
    "어울리는 한 줄 반응 두 개를 제안한다."
)
