"""간단한 규칙 기반 Safety Guardrail.

한계: 키워드/패턴 기반의 최소 안전장치이며 완전한 검열 시스템이 아니다.
LLM 사용 시에는 시스템 프롬프트의 안전 규칙이 함께 적용된다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

SELF_HARM = re.compile(r"(자살|자해|죽고\s*싶|목숨을?\s*끊|사라지고\s*싶)")
HATE_TERMS = ("맘충", "김치녀", "된장녀", "한남충", "틀딱", "병신", "찐따", "장애인 같", "급식충")
HARASS = re.compile(r"(죽어라|죽여버|꺼져\s*라|패죽|성폭행|강간)")
IMPERSONATE = re.compile(r"(성대모사|흉내|말투로|처럼\s*말해|인 척)")
PII = re.compile(r"(\b\d{6}-\d{7}\b|\b01[016789]-?\d{3,4}-?\d{4}\b|[\w.+-]+@[\w-]+\.[\w.]+)")

SELF_HARM_MESSAGE = (
    "지금 많이 힘든 이야기를 해주셨네요. 이 대화에서는 유머보다 안전이 먼저예요. "
    "혼자 감당하기 어렵다면 가까운 사람이나 전문가에게 꼭 이야기해주세요. "
    "한국에서는 자살예방상담전화 109(24시간)로 연결할 수 있어요. 급한 위험이 있다면 112/119에 연락해주세요."
)


@dataclass
class SafetyResult:
    level: str = "ok"  # ok | warn | block
    reasons: list[str] = field(default_factory=list)
    self_harm: bool = False
    impersonation: bool = False
    pii: bool = False


def check_text(text: str) -> SafetyResult:
    r = SafetyResult()
    if SELF_HARM.search(text):
        r.level, r.self_harm = "block", True
        r.reasons.append("자해·자살 관련 표현")
    if HARASS.search(text):
        r.level = "block"
        r.reasons.append("위협·폭력·성폭력 표현")
    hits = [t for t in HATE_TERMS if t in text]
    if hits:
        if len(hits) > 1:
            r.level = "block"
        elif r.level == "ok":
            r.level = "warn"
        r.reasons.append("특정 집단을 비하하는 표현: " + ", ".join(hits))
    if IMPERSONATE.search(text):
        r.impersonation = True
    if PII.search(text):
        r.pii = True
        if r.level == "ok":
            r.level = "warn"
        r.reasons.append("개인정보로 보이는 문자열 (전화번호/이메일/주민번호 형태)")
    return r


def safe_output(text: str) -> str:
    """모델 출력에 대한 마지막 방어선."""
    res = check_text(text)
    if res.level == "block" and not res.self_harm:
        return "그 방향의 농담은 누군가에게 상처가 될 수 있어서 접어둘게요. 다른 결로 다시 웃겨볼까요?"
    return text
