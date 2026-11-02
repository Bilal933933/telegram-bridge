"""محرّك Qoder CLI: بثّ تفاعلي، جلسات، نماذج، وإيقاف المهمة الجارية."""
from __future__ import annotations

import json
import os
import subprocess

import config
from bridge.core.errors import EngineError
from bridge.core.models import StreamResult
from bridge.infrastructure.engines.qoder import cli_runner, history_log


class QoderEngine:
    kind = "qoder"
    supports_projects = False
    supports_agents = False
    supports_permissions = False

    def __init__(self):
        self._proc = None

    # ---------- عقد AgentEngine ----------

    def list_sessions(self, workdir, limit=20):
        _, out, err = cli_runner.run(["--list-sessions", "-w", workdir])
        return cli_runner.parse_sessions(out + "\n" + err)[:limit]

    def create_session(self, workdir, title):
        raise EngineError("Qoder لا ينشئ جلسات مسبقًا — أرسل رسالة لتبدأ محادثة.")

    def stream(self, prompt, *, session_id, workdir, model, on_delta, on_tool,
               on_permission=None):
        cmd = [config.QODER, "-p", prompt, "-o", "stream-json", "-w", workdir,
               "--permission-mode", config.QODER_MODE]
        if model:
            cmd += ["-m", model]
        if session_id:
            cmd += ["--resume", session_id]  # --session-id تُنشئ جلسة، والاستئناف بـ --resume
        flags = 0x08000000 if os.name == "nt" else 0
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                cwd=workdir if os.path.isdir(workdir) else None,
                                text=True, encoding="utf-8", errors="replace", bufsize=1,
                                creationflags=flags)
        self._proc = proc
        text = ""
        sid = session_id
        error = None
        noise = []
        try:
            for line in proc.stdout:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except ValueError:
                    noise.append(line)
                    continue
                etype = ev.get("type")
                if etype == "assistant":
                    for block in (ev.get("message") or {}).get("content") or []:
                        btype = block.get("type")
                        if btype == "text" and block.get("text"):
                            text = block["text"] if not text else text + block["text"]
                            on_delta(text)
                        elif btype == "tool_use":
                            on_tool(block.get("name") or "tool",
                                    json.dumps(block.get("input") or {}, ensure_ascii=False))
                elif etype == "result":
                    sid = ev.get("session_id") or sid
                    if ev.get("is_error"):
                        error = str(ev.get("result"))[:500]
                    elif not text and ev.get("result"):
                        text = ev["result"]
                        on_delta(text)
            proc.wait()
        finally:
            if proc.poll() is None:
                proc.kill()
            self._proc = None
        if not text and not error:
            detail = " · ".join(noise[-2:]).strip() if noise else ""
            error = detail or f"Qoder لم يُرجع ردًا (رمز الخروج {proc.returncode})"
        return StreamResult(text=text, session_id=sid, error=error)

    def interrupt(self, session_id=None):
        proc = self._proc
        if proc and proc.poll() is None:
            proc.kill()
            return True
        return False

    def is_active(self, session_id):
        proc = self._proc
        return bool(proc and proc.poll() is None)

    def list_models(self, workdir):
        _, out, _ = cli_runner.run(["--list-models", "-w", workdir], timeout=45)
        return cli_runner.parse_models(out)

    def history(self, session_id, limit=40):
        return history_log.read_messages(session_id, limit)

    # ---------- إضافات Qoder ----------

    def log_turn(self, session_id, user_text, assistant_text="", error=None):
        history_log.log_turn(session_id, user_text, assistant_text, error)
