"""스마트 라우터 서버 — OpenAI 호환 API.

    uv run server.py                       # http://127.0.0.1:8080/v1  (분류기: hybrid)
    CLASSIFIER=score PORT=9000 uv run server.py

브라우저로 http://127.0.0.1:8080 을 열면 채팅 페이지(chat/)가 뜬다.

들어온 /v1/chat/completions 요청의 마지막 사용자 메시지를 분류해
작은 모델 또는 큰 모델로 보내고, 답을 그대로 돌려준다.
model 값이 "small"이나 "big"이면 분류 없이 그 모델로 보낸다 (비교용).

어떤 모델이 골라졌는지는 응답 헤더 x-router-* 와 JSON의 "router" 필드에 담긴다.
"""

from __future__ import annotations

import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # 루트의 llm.py를 쓰기 위해

import llm  # noqa: E402
from classifiers import CLASSIFIERS  # noqa: E402

HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8080"))
CLASSIFIER = os.environ.get("CLASSIFIER", "hybrid")
UPSTREAM = llm.BASE_URL.rstrip("/") + "/chat/completions"
CHAT_DIR = (Path(__file__).resolve().parent.parent / "chat").resolve()  # 빌드된 채팅 페이지


def last_user_text(messages: list[dict]) -> str:
    """대화 전체가 아니라 가장 최근 사용자 메시지의 텍스트만 분류한다."""
    for m in reversed(messages):
        if m.get("role") != "user":
            continue
        content = m.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):  # [{"type": "text", "text": ...}, ...] 형식
            return " ".join(p.get("text", "") for p in content if p.get("type") == "text")
    return ""


def choose(body: dict) -> tuple[str, str]:
    if body.get("model") in llm.MODELS:  # "small" / "big" 직접 지정
        return body["model"], "지정"
    result = CLASSIFIERS[CLASSIFIER](last_user_text(body.get("messages", [])))
    return result if isinstance(result, tuple) else (result, "")


def upstream_request(body: dict) -> urllib.request.Request:
    return urllib.request.Request(
        UPSTREAM,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {llm.API_KEY}"},
        method="POST",
    )


class Handler(BaseHTTPRequestHandler):
    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Expose-Headers",
                         "x-router-size, x-router-model, x-router-note, x-router-price")

    def _json(self, status: int, payload: dict, extra_headers: dict | None = None) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        for k, v in (extra_headers or {}).items():
            self.send_header(k, v)
        self._cors()
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self) -> None:
        if self.path.rstrip("/") == "/v1/models":
            ids = ["router", *llm.MODELS]
            self._json(200, {"object": "list", "data": [{"id": i, "object": "model"} for i in ids]})
        else:
            self._static()

    def _static(self) -> None:
        """채팅 페이지(chat/)의 파일을 돌려준다."""
        rel = urllib.parse.unquote(urllib.parse.urlsplit(self.path).path).lstrip("/") or "index.html"
        file = (CHAT_DIR / rel).resolve()
        if not file.is_relative_to(CHAT_DIR) or not file.is_file():
            self._json(404, {"error": {"message": "not found"}})
            return
        data = file.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(file.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self) -> None:
        if self.path.rstrip("/") != "/v1/chat/completions":
            self._json(404, {"error": {"message": "not found"}})
            return
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        except (ValueError, json.JSONDecodeError):
            self._json(400, {"error": {"message": "JSON 본문이 필요합니다"}})
            return

        start = time.perf_counter()
        size, note = choose(body)
        body["model"] = llm.MODELS[size]
        if body.get("stream"):
            body["stream_options"] = {"include_usage": True}  # 스트림 끝에서 토큰 수를 받기 위해
        router_headers = {"x-router-size": size, "x-router-model": llm.MODELS[size],
                          "x-router-note": urllib.parse.quote(note),  # 헤더는 ASCII만 되므로 인코딩
                          "x-router-price": "{},{}".format(*llm.PRICES[size])}  # 1M 토큰당 USD (입력,출력)

        try:
            resp = urllib.request.urlopen(upstream_request(body), timeout=120)
        except urllib.error.HTTPError as e:
            self._json(e.code, json.loads(e.read() or b"{}"), router_headers)
            return
        except OSError as e:
            self._json(502, {"error": {"message": f"모델 서버 연결 실패: {e}"}}, router_headers)
            return

        with resp:
            if body.get("stream"):
                usage = self._relay_stream(resp, router_headers)
            else:
                payload = json.loads(resp.read())
                usage = payload.get("usage") or {}
                payload["router"] = {"size": size, "model": llm.MODELS[size], "note": note,
                                     "cost": llm.cost_of(size, usage.get("prompt_tokens", 0),
                                                         usage.get("completion_tokens", 0))}
                self._json(200, payload, router_headers)

        tokens_in, tokens_out = usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)
        print(f"[router] {size:<5} {llm.MODELS[size]}  {note}  "
              f"토큰 {tokens_in}+{tokens_out}  ${llm.cost_of(size, tokens_in, tokens_out):.6f}  "
              f"{time.perf_counter() - start:.1f}s", flush=True)

    def _relay_stream(self, resp, router_headers: dict) -> dict:
        """SSE 응답을 받는 대로 넘겨 주고, 마지막 usage 조각을 기억해 둔다."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        for k, v in router_headers.items():
            self.send_header(k, v)
        self._cors()
        self.end_headers()
        usage: dict = {}
        for line in resp:
            self.wfile.write(line)
            self.wfile.flush()
            if line.startswith(b"data: {"):
                chunk = json.loads(line[6:])
                usage = chunk.get("usage") or usage
        return usage

    def log_message(self, fmt, *args) -> None:  # 기본 접근 로그는 끄고 [router] 줄만 남긴다
        pass


if __name__ == "__main__":
    if CLASSIFIER not in CLASSIFIERS:
        raise SystemExit(f"CLASSIFIER는 {list(CLASSIFIERS)} 중 하나여야 합니다.")
    print(f"[router] http://{HOST}:{PORT}/v1  분류기={CLASSIFIER}  "
          f"small={llm.MODELS['small']}  big={llm.MODELS['big']}")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
