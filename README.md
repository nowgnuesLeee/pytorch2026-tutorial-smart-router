# pytorch2026-tutorial-smart-router

**나만의 작고 소중한 스마트 LLM 라우터 만들기**: PyTorch 2026 튜토리얼

"간단한 구현인데 비싼 모델을 써야 하나?"라는 고민에서 시작합니다. 쉬운 요청은 작은 모델로, 어려운 요청은 큰 모델로 보내 주는 스마트 라우터를 프레임워크 없이 Python으로 직접 만듭니다.

## 디렉터리

| 폴더 | 용도 |
| :--- | :--- |
| [`tutorial-1/`](./tutorial-1) | **1단계 시작점**: 키워드 분류기 `keyword` |
| [`tutorial-2/`](./tutorial-2) | **2단계 시작점**: 점수 분류기 `score` (1단계 완성됨) |
| [`tutorial-3/`](./tutorial-3) | **3단계 시작점**: LLM 분류기 `llm`, `hybrid` (1·2단계 완성됨) |
| [`final/`](./final) | **완성본**: 분류기 네 개 + OpenAI 호환 라우터 서버 |
| [`chat/`](./chat) | 채팅 페이지 빌드 결과 (React + Vercel AI SDK). 라우터 서버가 `/`에서 띄워 줌 |
| [`llm.py`](./llm.py) | 모든 단계가 함께 쓰는 토큰 팩토리 호출 (토큰 수·시간 기록) |
| [`questions.json`](./questions.json) | 질문 세트 (질문, 정답 모델, 함정 설명) |
| [`ppt/`](./ppt) | 발표 자료 (Marp 원본 `.md`와 `.pdf`): 도입, 1~4단계, 마무리 |
| [`SESSION_INTRO.md`](./SESSION_INTRO.md) | 행사 홈페이지용 세션 소개 |

단계 폴더의 파일:

| 파일 | 역할 | 실습에서 |
| :--- | :--- | :--- |
| `classifiers.py` | 분류기: 질문을 보고 `"small"` 또는 `"big"`을 고름 | **여기의 `TODO`를 채웁니다** |
| `run.py` | 질문 세트를 분류기에 넣고 결과를 표로 보여 줌 | 실행만 |
| `server.py` | 라우터 서버 (`final/`에만 있음) | 4단계 |

## 빠른 시작

[uv](https://docs.astral.sh/uv/)만 있으면 됩니다. Python과 패키지는 uv가 알아서 준비합니다.

```bash
# uv 설치 (처음 한 번)
curl -LsSf https://astral.sh/uv/install.sh | sh      # macOS / Linux
# powershell -c "irm https://astral.sh/uv/install.ps1 | iex"   # Windows

git clone https://github.com/nowgnuesLeee/pytorch2026-tutorial-smart-router.git
cd pytorch2026-tutorial-smart-router

cp .env.example .env       # 열어서 토큰 팩토리 주소·키·모델 이름 채우기
uv sync                    # Python 3.12 + 의존성 설치
```

`.env`는 `.gitignore`에 있으니 키를 넣어도 커밋되지 않습니다.

```bash
uv run llm.py "파이썬에서 리스트를 뒤집는 방법은?"   # 도입: 두 모델 비교 (루트에서)

cd tutorial-1
uv run run.py keyword --no-answer                   # 분류만
uv run run.py keyword                               # 분류 + 고른 모델로 답 받기
```

## 진행 순서

| 순서 | 내용 | 발표 자료 | 시간 |
| :--- | :--- | :--- | :---: |
| 도입 | AI 시대를 대비하는 방법, LLM 라우터와 스마트 LLM 라우터 | `intro` | 10분 |
| 1단계 | 키워드 기반 분류: `llm.py`로 두 모델 비교, 키워드 분류기와 그 빈틈 | `tutorial-1` | 15분 |
| 2단계 | 가중치 기반 분류: 시그널별 가중치를 더한 점수 분류기 | `tutorial-2` | 25분 |
| 3단계 | LLM 분류: 구조화 출력(JSON 스키마)으로 작은 모델에게 판정 맡기기, 실패하면 점수로 되돌아가기, 경계 근처에서만 LLM 부르기(`hybrid`) | `tutorial-3` | 25분 |
| 4단계 | 채팅 페이지에서 확인: 분류기를 OpenAI 호환 서버로 띄워 대화하기 | `tutorial-4` | 35분 |
| 마무리 | 토큰 최적화(라우터 뒷단의 캐시), Continuum Router & Hub, 래블업의 토큰 팩토리, 질의응답 | `end` | 10분 |

## run.py 사용법

```bash
uv run run.py keyword               # 분류 + 답변 (답변용으로 모델을 호출해 토큰을 씁니다)
uv run run.py score --no-answer     # 분류만
uv run run.py all --no-answer       # 지금 폴더의 분류기를 모두 비교
uv run run.py hybrid --only 18,20   # 일부 질문만
```

출력 예시:

```text
=== score ===
✅  1 small 안녕? 오늘 기분 어때?                      score=-0.30
❌ 20 big   인생의 버그 같은 순간에 대한 짧은 시를 써줘.         score=+0.35
── 정확도 20/24 · 분류용 LLM 호출 0회 · 평균 분류 0ms
```

답변까지 받으면 마지막 줄에 쓴 토큰 합계(분류용 포함)를 보여 줍니다.

## 라우터 서버 (final/)

```bash
cd final
uv run server.py                          # http://127.0.0.1:8080 (채팅 페이지), 분류기 hybrid
CLASSIFIER=score PORT=9000 uv run server.py
```

- `POST /v1/chat/completions`: 마지막 사용자 메시지를 분류해 작은 모델 또는 큰 모델로 보냅니다. 스트리밍(`"stream": true`)도 됩니다.
- `model`이 `"small"`이나 `"big"`이면 분류 없이 그 모델로 보냅니다 (비교용).
- `GET /v1/models`: `router`, `small`, `big`
- 어떤 모델이 골라졌는지는 응답 헤더 `x-router-size`, `x-router-model`, `x-router-note`(URL 인코딩)와, 스트리밍이 아닐 때 JSON의 `router` 필드에 담깁니다.
- `GET /`: 채팅 페이지(`chat/`). 브라우저로 `http://127.0.0.1:8080`을 열면 바로 대화할 수 있습니다.
- 다른 채팅 앱에서도 부를 수 있도록 CORS를 열어 두었습니다.

```bash
curl http://127.0.0.1:8080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model": "router", "messages": [{"role": "user", "content": "안녕?"}]}'
```

## 설정 (.env)

| 변수 | 의미 |
| :--- | :--- |
| `LLM_BASE_URL`, `LLM_API_KEY` | 토큰 팩토리 OpenAI 호환 엔드포인트와 키 |
| `SMALL_MODEL`, `BIG_MODEL` | 작은 모델, 큰 모델 이름 |
| `QUESTIONS` | (선택) 다른 질문 세트 파일 경로 |
| `CLASSIFIER`, `HOST`, `PORT` | (선택) 서버 설정 |

이미 `export`한 환경변수가 있으면 `.env`보다 우선합니다.

요구 환경: [uv](https://docs.astral.sh/uv/) (Python 3.12는 uv가 설치). GPU 불필요.
