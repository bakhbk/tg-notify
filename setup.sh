#!/usr/bin/env bash
# Сделает tg-notify глобально доступным:
#   1) создаст/проверит .venv и установит пакет в editable-режим
#   2) положит симлинк ~/.local/bin/tg-notify -> .venv/bin/tg-notify
set -euo pipefail
cd "$(dirname "$0")"

# 1) venv + editable install
if [ ! -x .venv/bin/python ]; then
    if command -v uv >/dev/null 2>&1; then
        uv venv && uv pip install -e .
    else
        python3 -m venv .venv
        .venv/bin/pip install -e .
    fi
fi

# 2) глобальный bin
mkdir -p "$HOME/.local/bin"
ln -sf "$PWD/.venv/bin/tg-notify" "$HOME/.local/bin/tg-notify"

if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo "⚠️  ~/.local/bin не в PATH. Добавьте в ~/.zshrc:"
    echo '  export PATH="$HOME/.local/bin:$PATH"'
    echo "  затем: source ~/.zshrc"
fi

echo "✅ tg-notify доступен глобально: $(command -v tg-notify || echo "$HOME/.local/bin/tg-notify")"
echo "   (токен берётся из .env текущего каталога или TG_TOKEN/TG_CHAT в окружении)"
