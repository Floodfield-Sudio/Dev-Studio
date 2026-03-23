#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  DevStudio Pro — Lanceur (macOS / Linux)
# ─────────────────────────────────────────────────────────────────────────────
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC_FILE="$SCRIPT_DIR/DevStudioPro.pyw"

# ── Répertoire d'installation selon l'OS ─────────────────────────────────────
OS="$(uname -s)"
case "$OS" in
    Darwin)
        APP_DIR="$HOME/Library/Application Support/FFS/DevStudio"
        ;;
    Linux)
        XDG_DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
        APP_DIR="$XDG_DATA/FFS/DevStudio"
        ;;
    *)
        APP_DIR="$HOME/.ffs/devstudio"
        ;;
esac

VENV_DIR="$APP_DIR/.venv"
APP_FILE="$APP_DIR/DevStudioPro.pyw"

echo ""
echo " ====================================================="
echo "   DevStudio Pro  |  IDE Python + Builder Minecraft"
echo " ====================================================="
echo " Dossier : $APP_DIR"
echo ""

# ── 1. Verifier Python 3 ─────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo "[ERREUR] python3 introuvable."
    echo " macOS : brew install python   ou   https://python.org"
    echo " Linux : sudo apt install python3 python3-venv"
    exit 1
fi
echo "[OK] $(python3 --version) detecte."

# ── 2. Verifier que le source existe ─────────────────────────────────────────
if [ ! -f "$SRC_FILE" ]; then
    echo "[ERREUR] DevStudioPro.pyw introuvable a cote de ce run.sh"
    exit 1
fi

# ── 3. Creer le dossier d'installation ───────────────────────────────────────
mkdir -p "$APP_DIR"

# ── 4. Copier / mettre a jour DevStudioPro.pyw ───────────────────────────────
if [ ! -f "$APP_FILE" ]; then
    cp "$SRC_FILE" "$APP_FILE"
    echo "[OK] DevStudioPro.pyw installe."
elif [ "$SRC_FILE" -nt "$APP_FILE" ]; then
    cp "$SRC_FILE" "$APP_FILE"
    echo "[INFO] DevStudioPro.pyw mis a jour."
else
    echo "[OK] DevStudioPro.pyw deja a jour."
fi

# ── 5. Creer le venv si absent ────────────────────────────────────────────────
if [ ! -d "$VENV_DIR" ]; then
    echo "[1/3] Creation du venv..."
    python3 -m venv "$VENV_DIR"
    echo "[1/3] Venv cree."
else
    echo "[1/3] Venv existant."
fi

# ── 6. Activer le venv ───────────────────────────────────────────────────────
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

# ── 7. Installer PyQt6 si absent ─────────────────────────────────────────────
echo "[2/3] Verification PyQt6..."
if ! python -c "import PyQt6" &>/dev/null; then
    echo "[2/3] Installation de PyQt6..."
    pip install --upgrade PyQt6 --quiet
    echo "[2/3] PyQt6 installe."
else
    echo "[2/3] PyQt6 OK."
fi

# ── 8. Lancer depuis APP_DIR ─────────────────────────────────────────────────
echo "[3/3] Lancement..."
echo ""
cd "$APP_DIR"

nohup python "$APP_FILE" "$@" >/dev/null 2>&1 &
LAUNCH_PID=$!
sleep 2
if ! kill -0 "$LAUNCH_PID" 2>/dev/null; then
    echo "[!] Probleme — relance en mode console..."
    python "$APP_FILE" "$@"
fi

deactivate
