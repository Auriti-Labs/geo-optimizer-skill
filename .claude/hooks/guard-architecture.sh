#!/bin/bash
# Hook PreToolUse: blocca violazioni architetturali in GEO Optimizer
#
# Regola 1: core/ non deve stampare (print, click.echo)
# Regola 2: niente requests.get/post diretti in src/ (usare fetch_url)
# Regola 3: niente allow_redirects=True in src/ (redirect gestiti manualmente)

INPUT=$(cat)

FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# Estrai il contenuto nuovo (Edit usa new_string, Write usa content)
NEW_CONTENT=$(echo "$INPUT" | jq -r '.tool_input.new_string // .tool_input.content // empty')

# Se non c'è file path o contenuto, lascia passare
if [[ -z "$FILE_PATH" || -z "$NEW_CONTENT" ]]; then
    exit 0
fi

# ── Regola 1: core/ non deve stampare ──────────────────────────────────────
if [[ "$FILE_PATH" == */core/* ]]; then
    if echo "$NEW_CONTENT" | grep -qE '\bprint\s*\(|click\.echo\s*\('; then
        echo "BLOCCATO: core/ non deve stampare. Le funzioni core ritornano dataclass, il layer cli/ formatta l'output." >&2
        exit 2
    fi
fi

# ── Regola 2: niente requests.get/post diretti in src/ ─────────────────────
if [[ "$FILE_PATH" == */src/geo_optimizer/* ]]; then
    # Ignora http.py (è l'unico file autorizzato a usare requests)
    if [[ "$FILE_PATH" != */utils/http.py ]]; then
        if echo "$NEW_CONTENT" | grep -qE 'requests\.(get|post|put|delete|head|patch)\s*\('; then
            echo "BLOCCATO: non usare requests.get() direttamente. Importare e usare fetch_url() da geo_optimizer.utils.http che include anti-SSRF + DNS pinning + streaming." >&2
            exit 2
        fi
    fi
fi

# ── Regola 3: niente allow_redirects=True ──────────────────────────────────
if [[ "$FILE_PATH" == */src/geo_optimizer/* ]]; then
    if echo "$NEW_CONTENT" | grep -qE 'allow_redirects\s*=\s*True'; then
        echo "BLOCCATO: non usare allow_redirects=True. I redirect sono gestiti manualmente in _fetch_with_manual_redirects() con rivalidazione anti-SSRF su ogni hop." >&2
        exit 2
    fi
fi

# Tutto OK
exit 0
