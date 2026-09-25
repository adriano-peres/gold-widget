#!/usr/bin/env bash
# Instalador do Ouro Widget — cria o atalho no Show Apps (+ autostart opcional).
# Uso:
#   ./install.sh              # só Show Apps (~/.local/share/applications)
#   ./install.sh --autostart  # Show Apps + iniciar junto com a sessão
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="$REPO_DIR/gold_widget.py"
TEMPLATE="$REPO_DIR/ouro-widget.desktop"
APP_DIR="$HOME/.local/share/applications"
AUTOSTART_DIR="$HOME/.config/autostart"
APP_FILE="$APP_DIR/ouro-widget.desktop"
AUTOSTART_FILE="$AUTOSTART_DIR/ouro-widget.desktop"
AUTOSTART=0

if [[ "${1:-}" == "--autostart" ]]; then
    AUTOSTART=1
elif [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    echo "Uso: ./install.sh [--autostart]"
    exit 0
elif [[ -n "${1:-}" ]]; then
    echo "Opção desconhecida: $1 (use --autostart ou nada)" >&2
    exit 1
fi

if [[ ! -f "$SCRIPT" ]]; then
    echo "ERRO: gold_widget.py não encontrado em $REPO_DIR" >&2
    exit 1
fi
if [[ ! -f "$TEMPLATE" ]]; then
    echo "ERRO: ouro-widget.desktop não encontrado em $REPO_DIR" >&2
    exit 1
fi

mkdir -p "$APP_DIR"
# Injeta o caminho real do repo no Exec (funciona em qualquer usuário/máquina).
sed "s|__GOLD_WIDGET_EXEC__|python3 $SCRIPT|" "$TEMPLATE" > "$APP_FILE"
chmod +x "$APP_FILE"

if [[ $AUTOSTART -eq 1 ]]; then
    mkdir -p "$AUTOSTART_DIR"
    cp "$APP_FILE" "$AUTOSTART_FILE"
    # Garante a chave de autostart mesmo se o template mudar um dia.
    grep -q "X-GNOME-Autostart-enabled" "$AUTOSTART_FILE" \
        || echo "X-GNOME-Autostart-enabled=true" >> "$AUTOSTART_FILE"
    echo "Autostart ativado: $AUTOSTART_FILE"
fi

if command -v desktop-file-validate >/dev/null 2>&1; then
    desktop-file-validate "$APP_FILE" && echo "Desktop validado: $APP_FILE"
else
    echo "(desktop-file-validate não instalado; pulando validação)"
fi

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APP_DIR" 2>/dev/null || true
fi

echo "OK! Procure 'Ouro Widget' no Show Apps."
echo "Se não aparecer de imediato, faça logout/login ou rode: gtk-launch ouro-widget"
