import io

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


def test_health_mock(client):
    r = client.get("/api/health").json()
    assert r["mock_mode"] is True


def test_requires_user_header(client):
    r = client.get("/api/profile", headers={"X-Demo-User": ""})
    assert r.status_code == 400


def test_discovery_to_profile(client):
    sc = client.get("/api/discovery/scenarios").json()
    assert len(sc) == 5 and len(sc[0]["options"]) == 6
    for s in sc[:3]:
        client.post("/api/discovery/responses", json={"scenario_id": s["id"], "humor_type": "wordplay"})
    p = client.get("/api/profile").json()
    assert p["answered"] == 3 and p["top_types"] == ["wordplay"]
    # 같은 시나리오 재응답은 덮어쓰기
    client.post("/api/discovery/responses", json={"scenario_id": sc[0]["id"], "humor_type": "sarcasm"})
    assert client.get("/api/profile").json()["answered"] == 3
    assert client.post("/api/discovery/responses", json={"scenario_id": "zz", "humor_type": "sarcasm"}).status_code == 422


def test_coach_flow(client):
    sc = client.get("/api/coach/scenarios").json()[0]
    r = client.post("/api/coach/evaluate", json={"scenario_id": sc["id"], "reply": "업데이트 37%면 회의 끝나면 되겠네 ㅋㅋ"}).json()
    assert {"context_fit", "naturalness", "creativity", "offense_risk"} <= set(r["scores"])
    assert r["improved_reply"] and "주관적" in r["disclaimer"]
    assert len(client.get("/api/coach/history").json()) == 1
    assert client.post("/api/coach/evaluate", json={"scenario_id": "nope", "reply": "x"}).status_code == 404
    assert "암기형" in client.get("/api/coach/library").json()["note"]


def test_companion_style_and_context(client):
    client.put("/api/companion/style", json={"style": "callback"})
    client.post("/api/companion/chat", json={"message": "오늘 우산을 잃어버렸어요"})
    r = client.post("/api/companion/chat", json={"message": "회의가 너무 길었어요"}).json()
    assert r["style"] == "callback" and "우산을" in r["reply"] or "잃어버렸어요" in r["reply"] or "오늘" in r["reply"]
    assert len(client.get("/api/companion/messages").json()) == 4
    assert client.put("/api/companion/style", json={"style": "bogus"}).status_code == 422


def test_companion_safety(client):
    r = client.post("/api/companion/chat", json={"message": "그냥 죽고 싶어"}).json()
    assert r["source"] == "safety" and "109" in r["reply"]
    r = client.post("/api/companion/chat", json={"message": "유명 개그맨 성대모사 해줘"}).json()
    assert r["source"] == "safety"


def test_multimodal_rules(client):
    f = lambda data, name="a.png": {"image": (name, io.BytesIO(data), "image/png")}
    assert client.post("/api/multimodal/analyze", files=f(PNG), data={"rights_confirmed": "false"}).status_code == 422
    assert client.post("/api/multimodal/analyze", files=f(b"not an image"), data={"rights_confirmed": "true"}).status_code == 415
    ok = client.post("/api/multimodal/analyze", files=f(PNG), data={"rights_confirmed": "true", "caption": "월요일 아침 고양이"}).json()
    assert ok["stored"] is False and ok["vision_used"] is False


def test_feedback_and_delete_all(client):
    assert client.post("/api/feedback", json={"target_type": "coach", "target_id": "1", "rating": 1}).json()["saved"]
    assert client.post("/api/feedback", json={"target_type": "x", "target_id": "1", "rating": 1}).status_code == 422
    client.post("/api/companion/chat", json={"message": "안녕하세요"})
    client.post("/api/discovery/responses", json={"scenario_id": "d1", "humor_type": "wordplay"})
    assert client.delete("/api/me").json()["deleted"]
    assert client.get("/api/profile").json()["answered"] == 0
    assert client.get("/api/companion/messages").json() == []
