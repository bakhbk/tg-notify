#!/usr/bin/env bash
# Сделает tg-notify глобально доступным:
#   1) создаст/проверит .venv и установит пакет в editable-режим
#   2) положит симлинк ~/.local/bin/tg-notify -> .venv/bin/tg-notify
#   3) положит симлинк ~/.config/tg-notify/.env -> ./.env (креды из любого каталога)
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

# 3) глобальные креды: tg-notify ищет .env в ~/.config/tg-notify/ из любого каталога
if [ -f .env ]; then
    mkdir -p "$HOME/.config/tg-notify"
    ln -sf "$PWD/.env" "$HOME/.config/tg-notify/.env"
else
    echo "⚠️  .env не найден — создайте его с TG_TOKEN и TG_CHAT, затем запустите setup.sh заново"
fi

if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo "⚠️  ~/.local/bin не в PATH. Добавьте в ~/.zshrc:"
    echo '  export PATH="$HOME/.local/bin:$PATH"'
    echo "  затем: source ~/.zshrc"
fi

echo "✅ tg-notify доступен глобально: $(command -v tg-notify || echo "$HOME/.local/bin/tg-notify")"
echo "   креды: --chat > TG_TOKEN/TG_CHAT в окружении > \$TG_NOTIFY_ENV > ~/.config/tg-notify/.env > ./.env"
