# Gag AI 

유머 취향, 즉흥 대화 반응, 맥락·타이밍을 이해하는 AI 서비스의 실행 가능한 MVP입니다.
단순 Joke Generator가 아니라 **취향 파악 → 반사신경 연습 → 대화형 컴패니언**으로 이어지는 구조입니다. 한국어 우선, 로그인 없는 로컬 데모, API Key 없이 Mock Mode로 end-to-end 실행됩니다.

## 기능
| 영역 | 내용 |
|---|---|
| Humor Discovery | 5개 상황에서 가장 웃긴 반응 선택 → 6개 유머 유형(말장난/시니컬/엉뚱/관찰/콜백/자기비하) 레이더 프로필 |
| Humor Reflex Coach | 상황+대화 제시 → 자유 답변 → 맥락·자연스러움·창의성·불쾌 가능성 평가, 개선 답변과 이유. 암기형 Joke Library와 상황 반응 연습을 분리. 모든 평가에 "주관적 의견" 표시 |
| AI Humor Companion | 프로필·이전 대화를 반영한 채팅, 유머 스타일 전환, 실존 인물 모방 거절, 안전 가드레일 |
| Multimodal 기반 | 권리 확인 후 이미지 업로드 → 분석(비전 지원 모델 연결 시). 저장·학습 사용 없음. 음성/영상은 후속 |
| 데이터 통제 | `DELETE /api/me` (UI: 프로필의 "내 데이터 모두 삭제") |

Human Matching은 구현하지 않았고, `ProfileSnapshot`(프로필 벡터, `matching_opt_in=False`)만 준비했습니다.

## 실행 (Python 3.11+, Node 20+)
```bash
# 1) 백엔드
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env        # 선택. 없어도 Mock Mode
uvicorn app.main:app --port 8000
```
```bash
# 2) 프론트엔드 (새 터미널)
cd frontend
npm install
npm run dev                    # http://localhost:5173 (/api 는 8000으로 프록시)
```

### 실제 LLM 연결
`.env`에서 `HUMOR_LLM_PROVIDER=anthropic` + `ANTHROPIC_API_KEY=...` (또는 `openai_compatible` + `OPENAI_API_KEY`, `OPENAI_MODEL`). Key가 없거나 호출이 실패하면 Mock으로 안전하게 대체됩니다. `.env`는 git에서 제외됩니다.

## 테스트
```bash
cd backend && python -m pytest -q     # API + 핵심 로직 14개
cd frontend && npm run build          # 타입체크 + 빌드
```

## 문서
[PRODUCT](docs/PRODUCT.md) · [ARCHITECTURE](docs/ARCHITECTURE.md) · [ROADMAP](docs/ROADMAP.md) · [DATA_SOURCES](docs/DATA_SOURCES.md)

## 정직한 한계
- 이 MVP는 **모델 학습/파인튜닝을 하지 않습니다.** 저장 데이터는 서비스 제공(기록·맥락)용입니다.
- Mock Mode의 평가·응답은 규칙/템플릿 기반이며 LLM 품질이 아닙니다.
- Safety Guardrail은 키워드/패턴 기반 최소 장치로 법적·윤리적 위험을 모두 해소하지 않습니다.
- 데모 사용자는 브라우저 랜덤 ID일 뿐 인증이 아닙니다. 공개 배포 전 인증이 필요합니다.

## Copyright & Usage / 저작권 및 이용

**English**

Copyright © 2026 Sihun Wang. All Rights Reserved.

This project is publicly available for viewing and portfolio demonstration purposes.

All rights to the original source code, documentation, designs, and project-specific assets are reserved by the author.

No permission is granted to reproduce, modify, redistribute, or commercially use the original materials without prior written authorization, except as permitted by applicable law or GitHub's Terms of Service.

Third-party libraries, dependencies, and other externally sourced materials remain subject to their respective licenses and ownership rights.

For licensing, collaboration, or commercial inquiries, please contact the repository owner.

**한국어**

저작권 © 2026 Sihun Wang. 모든 권리 보유.

이 프로젝트는 열람 및 포트폴리오 시연 목적으로 공개되어 있습니다.

원본 소스 코드, 문서, 디자인 및 프로젝트 고유 자산에 대한 모든 권리는 저작자에게 있습니다.

관련 법령 또는 GitHub 이용약관에서 허용하는 경우를 제외하고, 사전 서면 허락 없이 원본 자료를 복제, 수정, 재배포하거나 상업적으로 이용할 수 없습니다.

제3자 라이브러리, 의존성 및 외부에서 가져온 자료는 각각의 라이선스와 소유권에 따릅니다.

라이선스, 협업, 상업적 문의는 저장소 소유자에게 연락해 주세요.
