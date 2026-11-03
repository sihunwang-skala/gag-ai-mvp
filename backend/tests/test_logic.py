from app.companion import mock_reply, pick_keyword, resolve_style
from app.content import COACH_SCENARIOS, DISCOVERY, HUMOR_TYPES
from app.evaluation import mock_evaluate
from app.profile import build_profile
from app.safety import check_text


def test_content_covers_all_types_in_every_scenario():
    for s in DISCOVERY:
        assert {t for t, _ in s["options"]} == set(HUMOR_TYPES)


def test_profile_vector():
    p = build_profile(["wordplay", "wordplay", "sarcasm"])
    assert p["vector"]["wordplay"] == 0.667 and p["top_types"] == ["wordplay", "sarcasm"]
    assert p["confidence"] == "low"
    assert build_profile([])["top_types"] == [] and build_profile([])["confidence"] == "none"


def test_safety():
    assert check_text("죽고 싶어").self_harm
    assert check_text("맘충 김치녀").level == "block"
    assert check_text("연락처 010-1234-5678").pii
    assert check_text("오늘 날씨 좋네요").level == "ok"
    assert check_text("아무개 성대모사 해줘").impersonation


def test_evaluate_context_and_risk():
    sc = COACH_SCENARIOS[0]
    good = mock_evaluate(sc, "업데이트가 37%에서 멈췄으면 회의는 우리가 먼저 시작하자 ㅋㅋ", [])
    bad = mock_evaluate(sc, "ㅇ", [])
    assert good["scores"]["context_fit"] > bad["scores"]["context_fit"]
    risky = mock_evaluate(sc, "맘충 같은 회의네", [])
    assert risky["scores"]["offense_risk"] >= 4 and risky["safety_flags"]
    assert good["disclaimer"] and good["improved_reply"]


def test_memorized_detection():
    sc = COACH_SCENARIOS[0]
    r = mock_evaluate(sc, "알람 시계가 면접에서 떨어진 이유? 사람들을 너무 많이 깨웠거든요.", [])
    assert r["memorized_joke_suspected"] and r["scores"]["creativity"] == 1


def test_companion_callback_uses_history_and_style_resolution():
    hist = [{"role": "user", "content": "오늘 지하철에서 우산을 놓쳤어요"}]
    assert pick_keyword(hist[0]["content"]) in mock_reply("회의가 길어졌어요", hist, "callback")
    assert resolve_style("auto", ["sarcasm"]) == "sarcasm" and resolve_style("wordplay", ["sarcasm"]) == "wordplay"
    assert pick_keyword("나는 커피숍") == "커피숍"
