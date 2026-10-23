"""Faux serveur LLM OpenAI-compatible pour tester omnibot-lite sans GPU.

- La 1re fois qu'un message user contient "visage", il renvoie un tool_call face_animation(happy).
- Si le message user contient "cherche", il renvoie un tool_call web_search (Tavily mocké sur /search).
- Sinon, il répond par un texte de remplissage en streaming.

Usage : python scripts/fake_llm_server.py [port]   (défaut 9999)
Puis :  OMNIBOT_LLM_BASE_URL=http://127.0.0.1:9999/v1
"""

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 9999


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _json(self, obj, code=200):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path.startswith("/v1/models"):
            self._json({"object": "list", "data": [{"id": "fake-model", "object": "model"}]})
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        if self.path.startswith("/search"):
            self._json({
                "answer": "Réponse mockée de Tavily pour le smoke test.",
                "results": [{
                    "title": "Résultat mocké",
                    "url": "https://example.com/mock",
                    "content": "Extrait mocké avec accents é, à et emoji 🦖 pour vérifier l'utf-8.",
                }],
            })
            return
        if not self.path.startswith("/v1/chat/completions"):
            self._json({"error": "not found"}, 404)
            return
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n) or b"{}")
        msgs = body.get("messages") or []
        # Ne raisonner que sur le tour courant : dernier message user + messages après lui.
        last_user_idx = max(
            (i for i, m in enumerate(msgs) if m.get("role") == "user"), default=len(msgs) - 1
        )
        user_texts = str(msgs[last_user_idx].get("content") or "")
        turn_msgs = msgs[last_user_idx:]
        has_tool_result = any(m.get("role") == "tool" for m in turn_msgs)

        if not has_tool_result and "cherche" in user_texts.lower():
            args = {"query": "info récente", "max_results": 3}
            if body.get("stream"):
                self._send_sse_named_tool_call("web_search", args)
            else:
                self._json({
                    "choices": [{"message": {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [{
                            "id": "call_fake_ws", "type": "function",
                            "function": {"name": "web_search", "arguments": json.dumps(args)},
                        }],
                    }}]
                })
            return

        tool_texts = " ".join(str(m.get("content") or "") for m in turn_msgs if m.get("role") == "tool")
        if "example.com/mock" in tool_texts:
            reply = "Recherche web intégrée — source : https://example.com/mock (extrait : é, à, 🦖)"
            if body.get("stream"):
                self._send_sse_text(reply)
            else:
                self._json({"choices": [{"message": {"role": "assistant", "content": reply}}]})
            return

        if not has_tool_result and "visage" in user_texts.lower():
            if body.get("stream"):
                self._send_sse_tool_call("happy")
            else:
                self._json({
                    "choices": [{"message": {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [{
                            "id": "call_fake1", "type": "function",
                            "function": {"name": "face_animation", "arguments": '{"animation":"happy"}'},
                        }],
                    }}]
                })
            return

        reply = "Bonjour ! Je suis le modèle factice — accents : é, è, à, âme ; apostrophe ’ typographique ; emoji 🐶. Configure un vrai serveur Strata ou Ollama."
        if body.get("stream"):
            self._send_sse_text(reply)
        else:
            self._json({"choices": [{"message": {"role": "assistant", "content": reply}}]})

    def _send_sse_text(self, text: str):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        for word in text.split(" "):
            chunk = {"choices": [{"delta": {"content": word + " "}}]}
            self.wfile.write(f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n".encode("utf-8"))
            self.wfile.flush()
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()

    def _send_sse_tool_call(self, animation: str):
        self._send_sse_named_tool_call("face_animation", {"animation": animation})

    def _send_sse_named_tool_call(self, name: str, args: dict):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        events = [
            {"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "call_fake1", "function": {"name": name}}]}}]},
            {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": json.dumps(args, ensure_ascii=False)}}]}}]},
        ]
        for e in events:
            self.wfile.write(f"data: {json.dumps(e)}\n\n".encode())
            self.wfile.flush()
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()


if __name__ == "__main__":
    print(f"Fake LLM on http://127.0.0.1:{PORT}/v1")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
