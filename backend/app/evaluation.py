"""Humor Evaluation: Reflex Coach 답변 평가.

mock 모드는 휴리스틱(키워드 겹침, 길이, 유머 장치 표지, 라이브러리 유사도, 불쾌감 패턴)을 쓴다.
점수는 1~5의 주관적 참고치이며 정답이 아니다.
"""
from __future__ import annotations

import json
import re
from difflib import SequenceMatcher

from .content import COACH_SCENARIOS, HUMOR_TYPES, JOKE_LIBRARY
from .llm.base import LLMError
from .safety import check_text

DISCLAIMER = "유머는 주관적이에요. 이 점수는 참고용 의견이며 정답이 아닙니다."
DEVICES = {
    "비유": re.compile(r"(처럼|같은|마치|듯)"),
    "과장": re.compile(r"(무려|세상|역대|평생|광속|우주|차원)"),
    "반전": re.compile(r"(근데|사실|알고 보니|그런데|하지만)"),
}


def get_scenario(sid: str) -> dict | None:
    return next((s for s in COACH_SCENARIOS if s["id"] == sid), None)


def _clamp(x: int) -> int:
    return max(1, min(5, x))


def _similar_library_joke(reply: str) -> str | None:
    for j in JOKE_LIBRARY:
        if SequenceMatcher(None, reply.strip(), j["text"]).ratio() > 0.6:
            return j["id"]
    return None


def improved_reply(scenario: dict, top_types: list[str]) -> tuple[str, str]:
    imps = scenario["improvements"]
    for t in top_types:
        if t in imps:
            return imps[t], t
    return imps["observational"], "observational"


def mock_evaluate(scenario: dict, reply: str, top_types: list[str]) -> dict:
    text = reply.strip()
    hits = [k for k in scenario["keywords"] if k in text]
    context_fit = _clamp(2 + len(hits))
    if len(text) < 4:
        context_fit = 1
    n = len(text)
    naturalness = 4 if 8 <= n <= 70 else (2 if n < 4 or n > 130 else 3)
    if re.search(r"[ㅋㅎ~?!]", text):
        naturalness = _clamp(naturalness + 1)
    devices = [name for name, rx in DEVICES.items() if rx.search(text)]
    creativity = _clamp(2 + len(devices))
    memorized = _similar_library_joke(text)
    if memorized:
        creativity = 1
    safety = check_text(text)
    risk = {"ok": 1, "warn": 4, "block": 5}[safety.level]

    strengths, issues = [], []
    if context_fit >= 4:
        strengths.append("상황의 핵심 요소(" + ", ".join(hits[:3]) + ")를 잘 짚었어요.")
    else:
        issues.append("상대의 말에서 구체적인 소재(예: " + ", ".join(scenario["keywords"][:2]) + ")를 하나 집어 쓰면 맥락 적절성이 올라가요.")
    if naturalness >= 4:
        strengths.append("대화에서 바로 말할 수 있는 자연스러운 길이와 톤이에요.")
    else:
        issues.append("너무 짧거나 길어요. 한두 문장으로 상대가 바로 받아칠 수 있게 다듬어보세요.")
    if creativity >= 4:
        strengths.append("유머 장치(" + ", ".join(devices) + ")가 있어서 창의적으로 느껴져요.")
    elif not memorized:
        issues.append("비유·과장·반전 중 하나를 더하면 평범한 반응에서 한 걸음 나아가요.")
    if memorized:
        issues.append("외워둔 농담과 매우 비슷해요. 상황을 이해한 반응이라기보다 암기형에 가까워 보여요.")
    if risk >= 4:
        issues.append("상대나 특정 집단에게 상처가 될 수 있는 표현이 있어요: " + "; ".join(safety.reasons))

    better, used = improved_reply(scenario, top_types)
    reasons = [f"{HUMOR_TYPES[used]['label']} 스타일로 상황의 소재를 직접 사용해 맥락 적절성을 높였어요.",
               "상대에게 되묻거나 공감을 덧붙여 대화가 이어지도록 했어요."]
    return {
        "scores": {"context_fit": context_fit, "naturalness": naturalness, "creativity": creativity, "offense_risk": risk},
        "strengths": strengths,
        "issues": issues,
        "improved_reply": better,
        "improved_style": used,
        "improvement_reasons": reasons,
        "memorized_joke_suspected": bool(memorized),
        "safety_flags": safety.reasons,
        "disclaimer": DISCLAIMER,
        "source": "mock",
    }


EVAL_SYSTEM = (
    "너는 한국어 유머 반사신경 코치다. 사용자의 즉흥 답변을 평가한다. 유머는 주관적이므로 단정하지 말고 건설적으로 말한다. "
    "특정 실존 인물을 모방하지 말고, 차별·혐오·괴롭힘을 부추기지 않는다. "
    "반드시 JSON 객체 하나만 출력한다. 키: context_fit, naturalness, creativity, offense_risk (각 1~5 정수, offense_risk는 높을수록 위험), "
    "strengths (문자열 배열), issues (문자열 배열), improved_reply (문자열), improvement_reasons (문자열 배열)."
)


def llm_evaluate(provider, scenario: dict, reply: str, top_types: list[str]) -> dict:
    prompt = (
        f"상황: {scenario['context']}\n상대의 말: {scenario['partner_line']}\n"
        f"사용자의 선호 유머 유형: {', '.join(HUMOR_TYPES[t]['label'] for t in top_types) or '미정'}\n"
        f"사용자의 답변: {reply}"
    )
    raw = provider.complete(EVAL_SYSTEM, [{"role": "user", "content": prompt}], max_tokens=900)
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        raise LLMError("평가 응답을 JSON으로 해석할 수 없습니다.")
    data = json.loads(m.group(0))
    scores = {k: _clamp(int(data[k])) for k in ("context_fit", "naturalness", "creativity", "offense_risk")}
    memorized = _similar_library_joke(reply)
    safety = check_text(reply)
    return {
        "scores": scores,
        "strengths": [str(x) for x in data.get("strengths", [])][:5],
        "issues": [str(x) for x in data.get("issues", [])][:5],
        "improved_reply": str(data["improved_reply"]),
        "improved_style": top_types[0] if top_types else "observational",
        "improvement_reasons": [str(x) for x in data.get("improvement_reasons", [])][:5],
        "memorized_joke_suspected": bool(memorized),
        "safety_flags": safety.reasons,
        "disclaimer": DISCLAIMER,
        "source": provider.name,
    }


def evaluate(provider, scenario: dict, reply: str, top_types: list[str]) -> dict:
    if not provider.is_mock:
        try:
            return llm_evaluate(provider, scenario, reply, top_types)
        except (LLMError, ValueError, KeyError, TypeError):
            res = mock_evaluate(scenario, reply, top_types)
            res["source"] = "mock_fallback"
            res["issues"].append("LLM 평가에 실패해 규칙 기반 평가로 대체했어요.")
            return res
    return mock_evaluate(scenario, reply, top_types)
