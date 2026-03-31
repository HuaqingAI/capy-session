#!/usr/bin/env python3
"""
HappyCapy Session Manager CLI

Config file: ~/.happycapy/capy-cli.json
Usage:
  capy-cli config --token TOKEN --cookies "COOKIE_STRING"
  capy-cli desktops [--limit 50] [--offset 0]
  capy-cli sessions DESKTOP_ID
  capy-cli create DESKTOP_ID TITLE [--model MODEL]
  capy-cli rename SESSION_ID TITLE
  capy-cli delete SESSION_ID [--force]
  capy-cli send SESSION_ID "message" [--wait] [--timeout 120]
"""

import argparse
import json
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("Error: 'requests' library not found. Run: pip install requests")
    sys.exit(1)

CONFIG_FILE = Path.home() / ".happycapy" / "capy-cli.json"
BASE_URL = "https://happycapy.ai/api"
DEFAULT_MODEL = "claude-sonnet-4-6"


# ─── Config ──────────────────────────────────────────────────────────────────

def load_config() -> dict:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {}


def save_config(config: dict):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)
    CONFIG_FILE.chmod(0o600)


def require_auth(config: dict):
    if not config.get("token"):
        print("Error: Not configured. Run: capy-cli config --token TOKEN --cookies COOKIES")
        sys.exit(1)


def get_headers(config: dict) -> dict:
    return {
        "accept": "application/json, text/plain, */*",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
        "authorization": f"Bearer {config['token']}",
        "content-type": "application/json",
        "origin": "https://happycapy.ai",
        "user-agent": "Mozilla/5.0 capy-cli/1.0",
    }


def get_cookies(config: dict) -> dict:
    """Parse cookie string into dict for requests."""
    raw = config.get("cookies", "")
    cookies = {}
    for part in raw.split(";"):
        part = part.strip()
        if "=" in part:
            k, _, v = part.partition("=")
            cookies[k.strip()] = v.strip()
    return cookies


# ─── API calls ───────────────────────────────────────────────────────────────

def api_get(config: dict, path: str, params: dict = None):
    r = requests.get(
        f"{BASE_URL}{path}",
        headers=get_headers(config),
        cookies=get_cookies(config),
        params=params,
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def api_post(config: dict, path: str, body: dict):
    r = requests.post(
        f"{BASE_URL}{path}",
        headers=get_headers(config),
        cookies=get_cookies(config),
        json=body,
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def api_patch(config: dict, path: str, body: dict):
    r = requests.patch(
        f"{BASE_URL}{path}",
        headers=get_headers(config),
        cookies=get_cookies(config),
        json=body,
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def api_delete(config: dict, path: str):
    r = requests.delete(
        f"{BASE_URL}{path}",
        headers=get_headers(config),
        cookies=get_cookies(config),
        timeout=15,
    )
    r.raise_for_status()
    return r.json() if r.content else {"success": True}


# ─── Commands ────────────────────────────────────────────────────────────────

def cmd_config(args):
    config = load_config()
    if args.token:
        config["token"] = args.token
    if args.cookies:
        config["cookies"] = args.cookies
    if not args.token and not args.cookies:
        # Show current config (masked)
        if not config:
            print("No config found.")
        else:
            token = config.get("token", "")
            print(f"Token:   {token[:20]}...{token[-10:] if len(token) > 30 else ''}")
            cookies = config.get("cookies", "")
            print(f"Cookies: {cookies[:60]}..." if len(cookies) > 60 else f"Cookies: {cookies}")
        return
    save_config(config)
    print(f"Config saved to {CONFIG_FILE}")


def cmd_desktops(args):
    config = load_config()
    require_auth(config)
    data = api_get(config, "/sessions", {"limit": args.limit, "offset": args.offset})
    sessions = data.get("sessions", data) if isinstance(data, dict) else data
    if not sessions:
        print("No desktops found.")
        return
    print(f"{'ID':<38}  {'Title':<35}  {'Model':<22}  {'Updated'}")
    print("-" * 110)
    for s in sessions:
        updated = s.get("updatedAt", "")[:19].replace("T", " ")
        print(f"{s['id']:<38}  {s.get('title',''):<35}  {s.get('model',''):<22}  {updated}")


def cmd_sessions(args):
    config = load_config()
    require_auth(config)
    data = api_get(config, f"/sessions/{args.desktop_id}/children")
    sessions = data.get("sessions", data) if isinstance(data, dict) else data

    print(f"Desktop: {args.desktop_id}\n")
    if not sessions:
        print("No sessions found.")
        return
    print(f"{'#':<4}  {'ID':<38}  {'Title':<35}  {'Model':<22}  {'Updated'}")
    print("-" * 116)
    for i, s in enumerate(sessions, 1):
        updated = s.get("updatedAt", "")[:19].replace("T", " ")
        print(f"{i:<4}  {s['id']:<38}  {s.get('title',''):<35}  {s.get('model',''):<22}  {updated}")


def cmd_create(args):
    config = load_config()
    require_auth(config)
    body = {
        "title": args.title,
        "model": args.model,
        "parentSessionId": args.desktop_id,
    }
    data = api_post(config, "/sessions", body)
    session = data.get("session", data)
    print(f"Created session: {session.get('id')}")
    print(f"  Title: {session.get('title')}")
    print(f"  Model: {session.get('model')}")


def cmd_rename(args):
    config = load_config()
    require_auth(config)
    data = api_patch(config, f"/sessions/{args.session_id}", {"title": args.title})
    session = data.get("session", data)
    print(f"Renamed session {args.session_id}")
    print(f"  New title: {session.get('title', args.title)}")


def cmd_delete(args):
    config = load_config()
    require_auth(config)
    if not args.force:
        confirm = input(f"Delete session {args.session_id}? [y/N] ").strip().lower()
        if confirm != "y":
            print("Aborted.")
            return
    api_delete(config, f"/sessions/{args.session_id}")
    print(f"Deleted session: {args.session_id}")


# ─── WebSocket send ──────────────────────────────────────────────────────────

def _extract_text(event: dict) -> tuple[str, bool]:
    """
    Try to pull printable text out of a WebSocket event.
    Returns (text, is_done).  is_done=True signals end-of-stream.
    """
    inner = event.get("data", {})
    if not isinstance(inner, dict):
        return "", False

    etype = inner.get("type", "")

    # End-of-stream markers
    if etype in ("message_stop", "end", "done", "complete"):
        return "", True

    content_obj = inner.get("data", {})
    if not isinstance(content_obj, dict):
        return "", False

    # Assistant message (full or delta)
    if etype in ("message", "message_delta"):
        content = content_obj.get("content", "")
        if isinstance(content, str):
            return content, False
        if isinstance(content, list):
            parts = [b.get("text", "") for b in content
                     if isinstance(b, dict) and b.get("type") == "text"]
            return "".join(parts), False

    # Streaming text delta
    if etype == "content_block_delta":
        delta = content_obj.get("delta", {})
        if isinstance(delta, dict) and delta.get("type") == "text_delta":
            return delta.get("text", ""), False

    return "", False


def cmd_send(args):
    config = load_config()
    require_auth(config)

    try:
        import websocket as ws_lib
    except ImportError:
        print("Error: 'websocket-client' not found. Run: pip install websocket-client")
        sys.exit(1)

    import time
    import threading
    from datetime import datetime, timezone

    token = config.get("token", "")
    cookie_str = config.get("cookies", "")
    ts = int(time.time() * 1000)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + f"{ts % 1000:03d}Z"

    payload = json.dumps({
        "type": "event",
        "sessionId": args.session_id,
        "data": {
            "id": f"temp-{ts}",
            "parent_id": None,
            "type": "message",
            "data": {"role": "user", "content": args.message},
            "created_at": now,
            "updated_at": now,
        },
    })

    state = {"sent": False, "error": None, "newline_needed": False}

    def on_open(ws):
        ws.send(payload)
        state["sent"] = True
        # Don't call ws.close() here — closing from within on_open
        # creates a race with the internal send buffer and sets sock=None
        # prematurely. For fire-and-forget, the main thread timeout closes it.

    def on_message(ws, raw):
        if not args.wait:
            return
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return
        text, done = _extract_text(data)
        if text:
            print(text, end="", flush=True)
            state["newline_needed"] = not text.endswith("\n")
        if done:
            if state["newline_needed"]:
                print()
            ws.close()

    def on_error(ws, error):
        state["error"] = str(error)

    def on_close(ws, *_):
        if state["newline_needed"]:
            print()

    ws = ws_lib.WebSocketApp(
        f"wss://happycapy.ai/ws?token={token}",
        header={"Origin": "https://happycapy.ai", "Cookie": cookie_str},
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
    )

    t = threading.Thread(target=ws.run_forever, kwargs={"ping_timeout": 10})
    t.daemon = True
    t.start()

    wait_secs = args.timeout if args.wait else 10
    t.join(timeout=wait_secs)
    if t.is_alive():
        ws.close()
        t.join(timeout=3)

    if state["error"]:
        print(f"Error: {state['error']}", file=sys.stderr)
        sys.exit(1)
    if not state["sent"]:
        print("Failed to connect or send message.", file=sys.stderr)
        sys.exit(1)
    if not args.wait:
        print(f"Message sent to session {args.session_id}")


# ─── Entry point ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="capy-cli",
        description="HappyCapy Session Manager",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # config
    p = sub.add_parser("config", help="View or update auth config")
    p.add_argument("--token", help="Bearer auth token")
    p.add_argument("--cookies", help="Full cookie string (from browser DevTools)")
    p.set_defaults(func=cmd_config)

    # desktops
    p = sub.add_parser("desktops", help="List desktops")
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--offset", type=int, default=0)
    p.set_defaults(func=cmd_desktops)

    # sessions
    p = sub.add_parser("sessions", help="List sessions in a desktop")
    p.add_argument("desktop_id", help="Desktop (parent session) ID")
    p.set_defaults(func=cmd_sessions)

    # create
    p = sub.add_parser("create", help="Create a new session in a desktop")
    p.add_argument("desktop_id", help="Desktop (parent session) ID")
    p.add_argument("title", help="Session title")
    p.add_argument("--model", default=DEFAULT_MODEL, help=f"Model (default: {DEFAULT_MODEL})")
    p.set_defaults(func=cmd_create)

    # rename
    p = sub.add_parser("rename", help="Rename a session")
    p.add_argument("session_id", help="Session ID")
    p.add_argument("title", help="New title")
    p.set_defaults(func=cmd_rename)

    # delete
    p = sub.add_parser("delete", help="Delete a session")
    p.add_argument("session_id", help="Session ID")
    p.add_argument("--force", "-f", action="store_true", help="Skip confirmation prompt")
    p.set_defaults(func=cmd_delete)

    # send
    p = sub.add_parser("send", help="Send a message to a session via WebSocket")
    p.add_argument("session_id", help="Session ID")
    p.add_argument("message", help="Message text to send")
    p.add_argument("--wait", "-w", action="store_true",
                   help="Stream and print the AI response (requires websocket-client)")
    p.add_argument("--timeout", "-t", type=int, default=120,
                   help="Max seconds to wait when --wait is set (default: 120)")
    p.set_defaults(func=cmd_send)

    args = parser.parse_args()
    try:
        args.func(args)
    except requests.HTTPError as e:
        print(f"API error {e.response.status_code}: {e.response.text[:200]}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(1)


if __name__ == "__main__":
    main()
