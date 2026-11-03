
import base64
import re
from typing import Annotated

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from . import companion, evaluation
from .config import Settings
from .content import COACH_SCENARIOS, COMPANION_STYLES, DISCOVERY, HUMOR_TYPES, JOKE_LIBRARY
from .db import CoachAttempt, DiscoveryResponse, Feedback, Message, ProfileSnapshot, User, make_session_factory, utcnow
from .llm.base import LLMError
from .llm.providers import get_provider
from .profile import build_profile
from .safety import check_text

USER_ID_RE = re.compile(r"^[A-Za-z0-9-]{8,64}$")
IMAGE_MAGIC = {b"\x89PNG\r\n\x1a\n": "image/png", b"\xff\xd8\xff": "image/jpeg", b"RIFF": "image/webp"}


def sniff_image(data: bytes) -> str | None:
    for magic, mime in IMAGE_MAGIC.items():
        if data.startswith(magic):
            if mime == "image/webp" and data[8:12] != b"WEBP":
                return None
            return mime
    return None


class DiscoveryIn(BaseModel):
    scenario_id: str
    humor_type: str


class CoachIn(BaseModel):
    scenario_id: str
    reply: str = Field(min_length=1, max_length=500)


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=800)


class StyleIn(BaseModel):
    style: str


class FeedbackIn(BaseModel):
    target_type: str
    target_id: str = Field(max_length=64)
    rating: int
    comment: str = Field(default="", max_length=500)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    SessionLocal = make_session_factory(settings.database_url)
    provider = get_provider(settings) if settings.llm_provider == "mock" else _safe_provider(settings)

    app = FastAPI(title="Gag AI MVP", version="0.1.0")
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"])

    def get_db():
        with SessionLocal() as db:
            yield db

    def current_user(db: Annotated[Session, Depends(get_db)], x_demo_user: Annotated[str | None, Header()] = None) -> User:
        if not x_demo_user or not USER_ID_RE.match(x_demo_user):
            raise HTTPException(400, "X-Demo-User 헤더(8~64자 영문/숫자/-)가 필요합니다.")
        user = db.get(User, x_demo_user)
        if not user:
            user = User(id=x_demo_user)
            db.add(user)
            db.commit()
        return user

    DB = Annotated[Session, Depends(get_db)]
    CurUser = Annotated[User, Depends(current_user)]

    def profile_of(db: Session, user: User) -> dict:
        picks = list(db.scalars(select(DiscoveryResponse.humor_type).where(DiscoveryResponse.user_id == user.id)))
        prof = build_profile(picks)
        snap = db.get(ProfileSnapshot, user.id) or ProfileSnapshot(user_id=user.id)
        snap.vector, snap.answered, snap.schema_version, snap.updated_at = prof["vector"], prof["answered"], prof["schema_version"], utcnow()
        db.merge(snap)
        db.commit()
        prof["types"] = {k: v["label"] for k, v in HUMOR_TYPES.items()}
        return prof

    @app.get("/api/health")
    def health():
        return {"status": "ok", "llm_provider": provider.name, "mock_mode": provider.is_mock, "supports_vision": provider.supports_vision}

    # --- A. Humor Discovery ---
    @app.get("/api/discovery/scenarios")
    def discovery_scenarios():
        return [{"id": s["id"], "situation": s["situation"],
                 "options": [{"humor_type": t, "text": txt} for t, txt in s["options"]]} for s in DISCOVERY]

    @app.post("/api/discovery/responses")
    def discovery_answer(body: DiscoveryIn, db: DB, user: CurUser):
        sc = next((s for s in DISCOVERY if s["id"] == body.scenario_id), None)
        if not sc or body.humor_type not in {t for t, _ in sc["options"]}:
            raise HTTPException(422, "알 수 없는 시나리오 또는 선택지입니다.")
        row = db.scalar(select(DiscoveryResponse).where(DiscoveryResponse.user_id == user.id, DiscoveryResponse.scenario_id == body.scenario_id))
        if row:
            row.humor_type, row.created_at = body.humor_type, utcnow()
        else:
            db.add(DiscoveryResponse(user_id=user.id, scenario_id=body.scenario_id, humor_type=body.humor_type))
        db.commit()
        return profile_of(db, user)

    @app.get("/api/profile")
    def get_profile(db: DB, user: CurUser):
        return profile_of(db, user)

    # --- B. Humor Reflex Coach ---
    @app.get("/api/coach/scenarios")
    def coach_scenarios():
        return [{k: s[k] for k in ("id", "title", "context", "partner_line")} for s in COACH_SCENARIOS]

    @app.get("/api/coach/library")
    def coach_library():
        return {"kind": "memorized_joke_library",
                "note": "암기형 농담입니다. 상황을 이해하고 반응하는 Reflex Practice와는 다른 연습이에요.",
                "jokes": [{"id": j["id"], "text": j["text"], "humor_type": j["type"]} for j in JOKE_LIBRARY]}

    @app.post("/api/coach/evaluate")
    def coach_evaluate(body: CoachIn, db: DB, user: CurUser):
        sc = evaluation.get_scenario(body.scenario_id)
        if not sc:
            raise HTTPException(404, "시나리오를 찾을 수 없습니다.")
        top = profile_of(db, user)["top_types"]
        result = evaluation.evaluate(provider, sc, body.reply, top)
        att = CoachAttempt(user_id=user.id, scenario_id=sc["id"], reply=body.reply, evaluation=result)
        db.add(att)
        db.commit()
        return {"attempt_id": att.id, **result}

    @app.get("/api/coach/history")
    def coach_history(db: DB, user: CurUser):
        rows = db.scalars(select(CoachAttempt).where(CoachAttempt.user_id == user.id).order_by(CoachAttempt.id.desc()).limit(20))
        return [{"id": r.id, "scenario_id": r.scenario_id, "reply": r.reply, "scores": r.evaluation["scores"], "created_at": r.created_at} for r in rows]

    # --- C. AI Humor Companion ---
    @app.get("/api/companion/styles")
    def companion_styles(user: CurUser):
        return {"current": user.companion_style, "options": [{"id": "auto", "label": "내 취향 자동"}, *[{"id": k, "label": v["label"]} for k, v in HUMOR_TYPES.items()]]}

    @app.put("/api/companion/style")
    def set_style(body: StyleIn, db: DB, user: CurUser):
        if body.style not in COMPANION_STYLES:
            raise HTTPException(422, "지원하지 않는 스타일입니다.")
        user.companion_style = body.style
        db.merge(user)
        db.commit()
        return {"current": user.companion_style}

    @app.get("/api/companion/messages")
    def messages(db: DB, user: CurUser):
        rows = db.scalars(select(Message).where(Message.user_id == user.id).order_by(Message.id.desc()).limit(50))
        return [{"id": m.id, "role": m.role, "content": m.content, "style": m.style} for m in reversed(list(rows))]

    @app.post("/api/companion/chat")
    def chat(body: ChatIn, db: DB, user: CurUser):
        recent = list(db.scalars(select(Message).where(Message.user_id == user.id).order_by(Message.id.desc()).limit(10)))
        history = [{"role": m.role, "content": m.content} for m in reversed(recent)]
        top = profile_of(db, user)["top_types"]
        out = companion.respond(provider, body.message, history, user.companion_style, top)
        db.add(Message(user_id=user.id, role="user", content=body.message, style=out["style"]))
        am = Message(user_id=user.id, role="assistant", content=out["reply"], style=out["style"])
        db.add(am)
        db.commit()
        return {"id": am.id, **out}

    @app.delete("/api/companion/messages")
    def clear_chat(db: DB, user: CurUser):
        db.execute(delete(Message).where(Message.user_id == user.id))
        db.commit()
        return {"deleted": True}

    # --- D. Multimodal 기반 (텍스트+이미지, 업로드는 저장하지 않음) ---
    @app.post("/api/multimodal/analyze")
    async def analyze_image(user: CurUser, image: UploadFile = File(...), caption: str = Form(""), rights_confirmed: bool = Form(False)):
        if not rights_confirmed:
            raise HTTPException(422, "이미지에 대한 권리를 보유하고 있음을 확인해야 합니다.")
        data = await image.read(settings.max_upload_bytes + 1)
        if len(data) > settings.max_upload_bytes:
            raise HTTPException(413, f"이미지는 {settings.max_upload_bytes // 1024 // 1024}MB 이하여야 합니다.")
        mime = sniff_image(data)
        if not mime:
            raise HTTPException(415, "PNG, JPEG, WebP 이미지만 지원합니다.")
        cap = caption.strip()[:300]
        if cap and check_text(cap).level == "block":
            raise HTTPException(422, "설명 문구에 허용되지 않는 표현이 있습니다.")
        base = {"stored": False, "mime": mime, "size_bytes": len(data), "note": "업로드한 이미지는 저장되지 않고 학습에 사용되지 않습니다. 이 요청 처리 후 폐기됩니다."}
        if provider.is_mock or not provider.supports_vision:
            return {**base, "source": "mock", "vision_used": False,
                    "analysis": "Mock 모드에서는 이미지 내용을 실제로 보지 못해요. 대신 입력한 설명을 바탕으로 구조를 추정했어요: "
                                + (f"'{cap}'" if cap else "(설명 없음)") + " — 기대와 실제의 대비가 있는지, 짧은 문구가 이미지 상황을 비트는지 살펴보면 좋아요.",
                    "suggested_reactions": ["이 상황은 설명이 필요 없는 장면이네요.", "저만 이게 너무 현실적으로 보이는 건가요?"]}
        try:
            text = provider.complete(companion.MM_SYSTEM, [{"role": "user", "content": cap or "이 이미지의 유머 맥락을 분석해줘."}],
                                     images=[(mime, base64.b64encode(data).decode())], max_tokens=500)
        except LLMError:
            raise HTTPException(502, "이미지 분석 모델 호출에 실패했습니다. 설정과 모델의 비전 지원 여부를 확인하세요.")
        return {**base, "source": provider.name, "vision_used": True, "analysis": text.strip(), "suggested_reactions": []}

    # --- User Feedback / 데이터 통제 ---
    @app.post("/api/feedback")
    def feedback(body: FeedbackIn, db: DB, user: CurUser):
        if body.target_type not in {"coach", "companion"} or body.rating not in (1, -1):
            raise HTTPException(422, "target_type 은 coach|companion, rating 은 1|-1 이어야 합니다.")
        db.add(Feedback(user_id=user.id, target_type=body.target_type, target_id=body.target_id, rating=body.rating, comment=body.comment))
        db.commit()
        return {"saved": True}

    @app.delete("/api/me")
    def delete_me(db: DB, user: CurUser):
        db.delete(user)  # FK ondelete=CASCADE (SQLite는 PRAGMA foreign_keys=ON)
        for model in (DiscoveryResponse, ProfileSnapshot, CoachAttempt, Message, Feedback):
            db.execute(delete(model).where(model.user_id == user.id))
        db.commit()
        return {"deleted": True}

    return app


def _safe_provider(settings: Settings):
    try:
        return get_provider(settings)
    except LLMError as e:
        print(f"[humor] {e} -> Mock Mode 로 시작합니다.")
        return get_provider(Settings(llm_provider="mock"))


app = create_app() if __name__ != "__main__" else None
