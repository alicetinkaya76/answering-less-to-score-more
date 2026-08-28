"""Yerel Ollama istemcisi. Tamamen stdlib (urllib). API çağrısı YOK; yalnız localhost.

Arayüz sözleşmesi (mockllm.MockClient de aynısını uygular):
    client.generate(prompt, model=..., options={...}, keep_alive=...) -> str
    client.digest(model) -> str | None
"""

import json
import time
import urllib.error
import urllib.request


class OllamaError(RuntimeError):
    pass


class OllamaClient:
    def __init__(self, base_url="http://localhost:11434", timeout=180, retries=3, backoff=5.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff

    # ---- düşük seviye ----
    def _post(self, path, payload):
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.base_url + path, data=data,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _get(self, path):
        req = urllib.request.Request(self.base_url + path, method="GET")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    # ---- kamu arayüzü ----
    def check(self):
        """Sunucu ayakta mı? Ayaktaysa kurulu model adlarını döndürür."""
        tags = self._get("/api/tags")
        return [m.get("name") for m in tags.get("models", [])]

    def digest(self, model):
        """Model digest'i (tekrarlanabilirlik kaydı için)."""
        try:
            tags = self._get("/api/tags")
            for m in tags.get("models", []):
                if m.get("name") == model or m.get("model") == model:
                    return m.get("digest")
        except Exception:
            pass
        try:
            show = self._post("/api/show", {"model": model})
            det = show.get("details", {}) or {}
            return show.get("digest") or det.get("digest")
        except Exception:
            return None

    def generate(self, prompt, model, options=None, keep_alive="30m"):
        """Tek atımlık üretim (stream kapalı). Hata halinde retries kadar dener."""
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": keep_alive,
        }
        if options:
            payload["options"] = dict(options)
        last = None
        for attempt in range(1, self.retries + 1):
            try:
                out = self._post("/api/generate", payload)
                return out.get("response", "")
            except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
                last = e
                if attempt < self.retries:
                    time.sleep(self.backoff * attempt)
        raise OllamaError(f"Ollama generate başarısız ({model}): {last}")
