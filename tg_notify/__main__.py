"""Core of the tg-notify CLI: send a text notification to a Telegram chat."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="tg-notify",
        description="Send a text notification to a Telegram chat.",
        epilog=(
            "recommended format (templates/notify.md):\n"
            "  <icon> <what> · <where>\n"
            "  <detail 1>\n"
            "  <detail 2>\n"
            "  icons: ✅ success | ❌ fail | ⚠️ warning | ℹ️ info\n"
            "  ≤4 lines, ≤200 chars, no greetings\n"
            "credentials: --chat flag > TG_CHAT env > .env (TG_TOKEN, TG_CHAT)"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("text", nargs="?", default=None, help="message text")
    parser.add_argument("--file", metavar="PATH", help="read message text from a file")
    parser.add_argument("--chat", metavar="ID", help="chat id (overrides TG_CHAT)")
    parser.add_argument("--silent", action="store_true", help="disable notification sound")
    parser.add_argument(
        "--truncate",
        type=int,
        default=500,
        metavar="N",
        help="max characters before truncation (0 = no limit)",
    )
    return parser.parse_args(argv)


def load_env(path: str | Path = ".env") -> dict[str, str]:
    """Parse a .env file, returning only TG_TOKEN / TG_CHAT if present."""
    result: dict[str, str] = {}
    p = Path(path)
    if not p.is_file():
        return result
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        if key in ("TG_TOKEN", "TG_CHAT"):
            result[key] = value
    return result


def truncate(text: str, limit: int) -> str:
    if limit == 0 or len(text) <= limit:
        return text
    return text[:limit] + f"\n[truncated, total {len(text)} chars]"


def send(token: str, chat_id: str, text: str, silent: bool) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps(
        {"chat_id": chat_id, "text": text, "disable_notification": silent}
    ).encode("utf-8")
    request = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        urllib.request.urlopen(request, timeout=10)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Telegram API returned HTTP {e.code}") from None
    except urllib.error.URLError as e:
        raise RuntimeError(f"network error: {e.reason}") from None
    except (TimeoutError, OSError) as e:
        raise RuntimeError(f"request failed: {e}") from None


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.text is not None:
        text = args.text
    elif args.file is not None:
        try:
            text = Path(args.file).read_text(encoding="utf-8")
        except OSError as e:
            print(f"❌ not sent: cannot read file: {e}")
            return 1
    else:
        print("❌ not sent: no text provided")
        return 1

    env_file = load_env()

    token = os.environ.get("TG_TOKEN") or env_file.get("TG_TOKEN")
    if not token:
        print("❌ not sent: TG_TOKEN not set")
        return 1

    chat = args.chat or os.environ.get("TG_CHAT") or env_file.get("TG_CHAT")
    if not chat:
        print("❌ not sent: TG_CHAT not set")
        return 1

    text = truncate(text, args.truncate)

    try:
        send(token, chat, text, args.silent)
    except Exception as e:
        print(f"❌ not sent: {e}")
        return 1

    print("✅ sent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
