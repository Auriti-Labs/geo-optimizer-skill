#!/usr/bin/env bash
# Riconcilia il sito pubblicato con Sanity: se un articolo live non è servito, rilancia
# il deploy. Da installare in cron sul server di produzione.
#
# Perché in pull invece che via webhook: la catena push-based si è rotta in silenzio il
# 2026-08-13 (secret del webhook verso un URL placeholder, workflow verde, pagina 404 per
# mezz'ora). Un controllo che interroga lo stato reale non ha secret da sbagliare, non
# espone porte, e si autoripara — se un giro fallisce, il successivo riprova.
#
# La decisione sta in check-live-drift.mjs, versionato e senza privilegi. Qui c'è solo
# l'azione, sul server dove vive lo script di rebuild.
#
# Installazione (crontab dell'utente che possiede il repo e lo script di rebuild):
#   17 * * * * /home/debian/geo-optimizer-skill/frontend/scripts/reconcile-live-site.sh
#
# Il minuto 17 è deliberato: evita lo :00, dove si accalcano tutti i cron del pianeta,
# e non collide con il rebuild giornaliero di 08:10.

set -euo pipefail

REPO="${GEO_REPO:-/home/debian/geo-optimizer-skill}"
REBUILD="${GEO_REBUILD_SCRIPT:-/home/debian/rebuild-geo-web.py}"
LOG="${GEO_RECONCILE_LOG:-/home/debian/logs/reconcile-live-site.log}"
LOCK="${GEO_RECONCILE_LOCK:-/tmp/reconcile-live-site.lock}"

log() {
  printf '[%s] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*" >>"$LOG"
}

# Un solo giro alla volta. Un rebuild dura oltre 120s: senza lock, due esecuzioni
# sovrapposte competerebbero per lo stesso repo e la stessa immagine Docker.
exec 9>"$LOCK"
if ! flock -n 9; then
  log "SKIP un altro giro è già in corso"
  exit 0
fi

cd "$REPO/frontend"

set +e
DRIFT_JSON="$(node scripts/check-live-drift.mjs --json 2>&1)"
DRIFT_EXIT=$?
set -e

case "$DRIFT_EXIT" in
  0)
    # Nessun log in caso di allineamento: 24 righe al giorno di "tutto ok"
    # seppelliscono le righe che contano.
    exit 0
    ;;
  10)
    log "DRIFT $DRIFT_JSON"
    ;;
  *)
    # Rete giù, Sanity irraggiungibile, sitemap non parsabile: non si deploya nel dubbio.
    log "ERRORE controllo drift (exit $DRIFT_EXIT): $DRIFT_JSON"
    exit 1
    ;;
esac

if [[ ! -x "$REBUILD" ]]; then
  log "ERRORE script di rebuild non eseguibile: $REBUILD"
  exit 1
fi

log "REBUILD avvio ($REBUILD --trigger reconcile)"
set +e
"$REBUILD" --trigger reconcile >>"$LOG" 2>&1
REBUILD_EXIT=$?
set -e

if [[ $REBUILD_EXIT -ne 0 ]]; then
  # Nessun retry qui: lo script di rebuild ha già la sua guardia anti-shrink e il
  # rollback automatico. Il prossimo giro di cron riprova, che è il retry.
  log "REBUILD fallito (exit $REBUILD_EXIT) — il prossimo giro riprova"
  exit 1
fi

# Verifica l'esito sullo stato reale, non sull'exit code: un rebuild che riporta
# successo senza risolvere il disallineamento è esattamente il modo in cui il
# webhook rotto è passato inosservato per due giorni.
set +e
node scripts/check-live-drift.mjs --json >/dev/null 2>&1
VERIFY_EXIT=$?
set -e

if [[ $VERIFY_EXIT -eq 0 ]]; then
  log "OK rebuild completato, sito allineato"
else
  log "ATTENZIONE rebuild completato ma il disallineamento persiste (exit $VERIFY_EXIT) — serve un occhio umano"
  exit 1
fi
