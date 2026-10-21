"""Hermes Agent adapter for Lightkeeper.

Hermes loads this file from ~/.hermes/plugins/lightkeeper/__init__.py: the whole
repo is the plugin (`hermes plugins install Light5566/claude-lightkeeper`). Claude
Code ignores this file and plugin.yaml.

It owns no vault logic. Every Hermes hook runs the same script Claude Code runs,
lib/hooks/run.py <hook>, as a subprocess with a JSON payload on stdin, and hands
the text that comes back to Hermes:

  pre_llm_call           -> session primer (first turn) and prompt hints
  transform_tool_result  -> the edit pointer, as a field in the JSON result of write_file / patch
  pre_verify             -> the Stop reminder, as a nudge that keeps the agent working
  on_session_finalize    -> the Stop reminder, as a notice to the user at session end

Stdlib only, Python 3.9.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUN = str(ROOT / "lib" / "hooks" / "run.py")
SKILLS = ("knowledge-vault", "vault-sync", "vault-tidy")
COMMANDS = ("init", "seed", "tidy", "trace", "release")
TIMEOUT = 10  # seconds per hook script, what hooks.json gives Claude Code

# Per-session dedup, keyed by the session_id Hermes passes to every hook.
_primed, _prompts = set(), {}


def _cwd():
    try:
        from agent.runtime_cwd import resolve_agent_cwd  # Hermes only
        return str(resolve_agent_cwd())
    except Exception:
        return os.getcwd()


def _hook(name, payload, **env):
    """Run one Lightkeeper hook script; its JSON object, or {} when silent or broken."""
    cwd = payload.setdefault("cwd", _cwd())
    try:
        r = subprocess.run([sys.executable, RUN, name], input=json.dumps(payload),
                           capture_output=True, text=True, timeout=TIMEOUT,
                           env={**os.environ, "CLAUDE_PROJECT_DIR": cwd, **env})
        return json.loads(r.stdout) if r.stdout.strip() else {}
    except Exception:
        return {}


def _context(name, payload):
    return (_hook(name, payload).get("hookSpecificOutput") or {}).get("additionalContext")


def pre_llm_call(session_id=None, user_message="", is_first_turn=False, **kw):
    sid = session_id or "unknown"
    parts = []
    if is_first_turn and sid not in _primed:  # once per session, whatever Hermes calls
        _primed.add(sid)
        primer = _context("session_start", {"session_id": sid, "source": "startup"})
        if primer:
            parts.append(primer + "\nThe procedures are skills: "
                         + ", ".join("lightkeeper:" + s for s in SKILLS + COMMANDS) + ".")
    if user_message and _prompts.get(sid) != user_message:  # once per user message
        _prompts[sid] = user_message
        parts.append(_context("prompt_hint", {"session_id": sid, "prompt": user_message}))
    text = "\n\n".join(p for p in parts if p)
    return {"context": text} if text else None


def transform_tool_result(tool_name=None, args=None, result=None, **kw):
    if tool_name not in ("write_file", "patch") or not isinstance(result, str):
        return None
    try:
        info = json.loads(result)
    except ValueError:
        return None
    if not isinstance(info, dict) or info.get("error"):
        return None
    path = info.get("resolved_path") or (args or {}).get("path")
    if not path:
        return None
    cwd = _cwd()
    path = os.path.abspath(os.path.expanduser(os.path.join(cwd, str(path))))  # join keeps an absolute path
    pointer = _context("file_guard", {"session_id": kw.get("session_id") or "unknown", "cwd": cwd,
                                      "tool_name": tool_name, "tool_input": {"file_path": path}})
    if not pointer:
        return None
    info["lightkeeper"] = pointer  # inside the JSON: Hermes parses this result to record the edit
    return json.dumps(info, ensure_ascii=False)


def pre_verify(session_id=None, attempt=0, **kw):
    if attempt:
        return None  # one nudge per answer; across turns, the vault moving is the loop breaker
    out = _hook("stop_reminder", {"session_id": session_id or "unknown"})
    msg = (out.get("hookSpecificOutput") or {}).get("additionalContext") or out.get("systemMessage")
    return {"action": "continue", "message": msg} if msg else None


def on_session_finalize(session_id=None, **kw):
    sid = session_id or "unknown"
    msg = _hook("stop_reminder", {"session_id": sid}, VAULT_STOP_NUDGE="quiet").get("systemMessage")
    _primed.discard(sid)
    _prompts.pop(sid, None)
    return {"message": msg} if msg else None


def _description(text):
    m = re.search(r"^description:\s*(.+)$", text, re.M)
    return m.group(1).strip() if m else ""


def _skills_dir():
    try:
        from plugins.plugin_storage import plugin_data_dir  # Hermes only
        return Path(plugin_data_dir("lightkeeper")) / "skills"
    except Exception:
        return Path(tempfile.gettempdir()) / "lightkeeper-skills"


def register(ctx):
    for name, fn in (("pre_llm_call", pre_llm_call), ("transform_tool_result", transform_tool_result),
                     ("pre_verify", pre_verify), ("on_session_finalize", on_session_finalize)):
        try:
            ctx.register_hook(name, fn)
        except Exception:
            pass  # a Hermes without this hook keeps the others
    for s in SKILLS:
        p = ROOT / "skills" / s / "SKILL.md"
        ctx.register_skill(s, str(p), description=_description(p.read_text()))
    out = _skills_dir()
    for c in COMMANDS:  # the Claude Code commands as skills: Hermes has neither placeholder
        try:
            src = (ROOT / "commands" / (c + ".md")).read_text()
            body = (src.replace("${CLAUDE_PLUGIN_ROOT}", str(ROOT))
                       .replace("$ARGUMENTS", "<the text after the skill name>"))
            dst = out / c / "SKILL.md"
            dst.parent.mkdir(parents=True, exist_ok=True)
            if not dst.is_file() or dst.read_text() != body:
                dst.write_text(body)
            ctx.register_skill(c, str(dst), description=_description(src))
        except Exception:
            pass  # an unwritable plugin-data dir loses the five procedures, not the hooks
