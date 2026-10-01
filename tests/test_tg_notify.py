"""Tests for the tg-notify CLI (tg_notify.__main__)."""

from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request

from tg_notify import __main__ as tg_main


def _patch_urlopen(monkeypatch, exc=None, return_value=None):
    calls = []

    def fake_urlopen(request, timeout=None):
        calls.append(request)
        if exc is not None:
            raise exc
        return return_value

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    return calls


def _set_env(monkeypatch, token="TOKEN", chat="CHAT"):
    if token is not None:
        monkeypatch.setenv("TG_TOKEN", token)
    else:
        monkeypatch.delenv("TG_TOKEN", raising=False)
    if chat is not None:
        monkeypatch.setenv("TG_CHAT", chat)
    else:
        monkeypatch.delenv("TG_CHAT", raising=False)


def _payload(request):
    return json.loads(request.data.decode("utf-8"))


def test_success(monkeypatch, capsys, tmp_path):
    monkeypatch.chdir(tmp_path)
    _set_env(monkeypatch)
    _patch_urlopen(monkeypatch, return_value=object())
    code = tg_main.main(["hello"])
    out = capsys.readouterr().out
    assert code == 0
    assert "✅ sent" in out


def test_http_401(monkeypatch, capsys, tmp_path):
    monkeypatch.chdir(tmp_path)
    _set_env(monkeypatch, token="SECRET_TOKEN")
    _patch_urlopen(
        monkeypatch,
        exc=urllib.error.HTTPError("http://x", 401, "Unauthorized", None, None),
    )
    code = tg_main.main(["hello"])
    out = capsys.readouterr().out
    assert code == 1
    assert "❌ not sent" in out
    assert "SECRET_TOKEN" not in out


def test_http_400(monkeypatch, capsys, tmp_path):
    monkeypatch.chdir(tmp_path)
    _set_env(monkeypatch)
    _patch_urlopen(
        monkeypatch,
        exc=urllib.error.HTTPError("http://x", 400, "Bad Request", None, None),
    )
    code = tg_main.main(["hello"])
    out = capsys.readouterr().out
    assert code == 1
    assert "❌ not sent" in out


def test_network_error(monkeypatch, capsys, tmp_path):
    monkeypatch.chdir(tmp_path)
    _set_env(monkeypatch)
    _patch_urlopen(monkeypatch, exc=urllib.error.URLError("no route"))
    code = tg_main.main(["hello"])
    out = capsys.readouterr().out
    assert code == 1
    assert "❌ not sent" in out


def test_timeout(monkeypatch, capsys, tmp_path):
    monkeypatch.chdir(tmp_path)
    _set_env(monkeypatch)
    _patch_urlopen(monkeypatch, exc=socket.timeout())
    code = tg_main.main(["hello"])
    out = capsys.readouterr().out
    assert code == 1
    assert "❌ not sent" in out


def test_missing_token(monkeypatch, capsys, tmp_path):
    monkeypatch.chdir(tmp_path)
    _set_env(monkeypatch, token=None, chat="CHAT")
    _patch_urlopen(monkeypatch, return_value=object())
    code = tg_main.main(["hello"])
    out = capsys.readouterr().out
    assert code == 1
    assert "❌ not sent: TG_TOKEN not set" in out


def test_missing_chat(monkeypatch, capsys, tmp_path):
    monkeypatch.chdir(tmp_path)
    _set_env(monkeypatch, token="TOKEN", chat=None)
    _patch_urlopen(monkeypatch, return_value=object())
    code = tg_main.main(["hello"])
    out = capsys.readouterr().out
    assert code == 1
    assert "❌ not sent: TG_CHAT not set" in out


def test_file_reading(monkeypatch, capsys, tmp_path):
    monkeypatch.chdir(tmp_path)
    _set_env(monkeypatch)
    f = tmp_path / "msg.txt"
    f.write_text("from file", encoding="utf-8")
    calls = _patch_urlopen(monkeypatch, return_value=object())
    code = tg_main.main(["--file", str(f)])
    assert code == 0
    assert _payload(calls[0])["text"] == "from file"


def test_truncate_500(monkeypatch, capsys, tmp_path):
    monkeypatch.chdir(tmp_path)
    _set_env(monkeypatch)
    text = "a" * 600
    calls = _patch_urlopen(monkeypatch, return_value=object())
    code = tg_main.main([text, "--truncate", "500"])
    assert code == 0
    assert _payload(calls[0])["text"] == "a" * 500 + "\n[truncated, total 600 chars]"


def test_truncate_0(monkeypatch, capsys, tmp_path):
    monkeypatch.chdir(tmp_path)
    _set_env(monkeypatch)
    text = "a" * 600
    calls = _patch_urlopen(monkeypatch, return_value=object())
    code = tg_main.main([text, "--truncate", "0"])
    assert code == 0
    assert _payload(calls[0])["text"] == text


def test_truncate_short(monkeypatch, capsys, tmp_path):
    monkeypatch.chdir(tmp_path)
    _set_env(monkeypatch)
    text = "a" * 100
    calls = _patch_urlopen(monkeypatch, return_value=object())
    code = tg_main.main([text, "--truncate", "500"])
    assert code == 0
    assert _payload(calls[0])["text"] == text


def test_silent(monkeypatch, capsys, tmp_path):
    monkeypatch.chdir(tmp_path)
    _set_env(monkeypatch)
    calls = _patch_urlopen(monkeypatch, return_value=object())
    code = tg_main.main(["hello", "--silent"])
    assert code == 0
    assert _payload(calls[0])["disable_notification"] is True


def test_chat_override(monkeypatch, capsys, tmp_path):
    monkeypatch.chdir(tmp_path)
    _set_env(monkeypatch, token="TOKEN", chat="999")
    calls = _patch_urlopen(monkeypatch, return_value=object())
    code = tg_main.main(["hello", "--chat", "123"])
    assert code == 0
    assert _payload(calls[0])["chat_id"] == "123"


def test_env_fallback(monkeypatch, capsys, tmp_path):
    monkeypatch.chdir(tmp_path)
    _set_env(monkeypatch, token=None, chat=None)
    (tmp_path / ".env").write_text(
        "TG_TOKEN=ENV_TOKEN\nTG_CHAT=ENV_CHAT\n", encoding="utf-8"
    )
    calls = _patch_urlopen(monkeypatch, return_value=object())
    code = tg_main.main(["hello"])
    out = capsys.readouterr().out
    assert code == 0
    assert "✅ sent" in out
    assert calls[0].full_url == "https://api.telegram.org/botENV_TOKEN/sendMessage"
    assert _payload(calls[0])["chat_id"] == "ENV_CHAT"


def test_no_input(monkeypatch, capsys, tmp_path):
    monkeypatch.chdir(tmp_path)
    _set_env(monkeypatch)
    _patch_urlopen(monkeypatch, return_value=object())
    code = tg_main.main([])
    out = capsys.readouterr().out
    assert code == 1
    assert "❌ not sent" in out


def test_help(monkeypatch, capsys, tmp_path):
    monkeypatch.chdir(tmp_path)
    try:
        code = tg_main.main(["-h"])
    except SystemExit as e:
        code = e.code
    out = capsys.readouterr().out
    assert code == 0
    for flag in ("--file", "--chat", "--silent", "--truncate"):
        assert flag in out
