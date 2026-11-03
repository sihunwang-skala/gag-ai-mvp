# Architecture (현재 구조)

```
React+TS+Vite ──/api──▶ FastAPI ──▶ SQLite (SQLAlchemy)
                          │
                          └─▶ LLM Provider Adapter: mock | anthropic | openai_compatible
```

## 모듈 (backend/app)
| 모듈 | 역할 | 독립 확장 포인트 |
|---|---|---|
| `profile.py` + `ProfileSnapshot` | Humor Profile 벡터(schema_version) | 매칭용 임베딩/유사도 |
| `companion.py` + `Message` | Conversation Context(최근 10턴) | 장기 메모리 |
| `evaluation.py` + `CoachAttempt` | Humor Evaluation | LLM-judge, 루브릭 개선 |
| `llm/` | 단일 `complete()` 인터페이스 | 제공자 추가 |
| `safety.py` | 입력·출력 가드레일 | 분류 모델 |
| `Feedback` | 사용자 평가(👍/👎) | 품질 개선 루프(동의 시) |
| `content.py` | 직접 작성한 Synthetic 데이터 | DB/CMS 이동 |

## 저장 데이터 vs 학습 데이터
- **저장(서비스용)**: 설문 응답, 코치 답변+평가, 대화, 피드백, 프로필 벡터. 사용자 삭제 API 제공.
- **학습용**: 없음. 이 MVP는 학습을 수행하지 않으며, 저장 데이터를 학습에 쓰려면 별도 명시 동의 필드와 파이프라인이 필요하다(로드맵).
- 업로드 이미지: 메모리에서만 처리, 저장 안 함.

## Creator Licensing (설계 수준)
Creator 동의 레코드(범위: 학습/스타일/수익배분, 철회 가능) → 라이선스된 데이터셋 버전 → Creator 스타일 어댑터. 현재 코드 없음. 동의·출처가 확인된 데이터만 수용한다.

## 결정과 Trade-off
- **SQLAlchemy + SQLite**: 의존성은 조금 늘지만 `DATABASE_URL`만 바꿔 PostgreSQL 전환 가능. 마이그레이션 도구(Alembic)는 스키마가 안정되면 도입.
- **SDK 대신 httpx 직접 호출**: 제공자 SDK 종속을 피하고 어댑터를 얇게 유지. 스트리밍 등은 미지원.
- **익명 `X-Demo-User` ID**: 로그인 없는 데모에 충분하나 인증이 아님.
- **Mock = 규칙/템플릿**: 데모·테스트 재현성 확보. 품질 평가는 실제 LLM에서 별도 필요.
- **Vector DB/Agent framework/마이크로서비스 미도입**: 현재 필요성 미검증.
