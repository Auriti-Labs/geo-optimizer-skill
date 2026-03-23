# Progress Log

## 2026-03-09 — Sessione iniziale

### Completato
- [x] Analisi completa geo-seo-claude (struttura, scoring, feature, storia commit)
- [x] Analisi stato attuale geo-optimizer-skill (scoring, plugin system, architettura)
- [x] Confronto obiettivo tra i due progetti
- [x] Creazione piano d'azione 5 fasi con priorità e file target

### Scoperte chiave
- Plugin system (CheckRegistry) pronto ma non integrato — primo blocco da risolvere
- geo-seo-claude ha 444 stelle con 9 commit e zero test — marketing > engineering
- Le 3 feature mancanti più impattanti: E-E-A-T, Brand Mentions, Platform Readiness
- Le 3 feature killer per superarlo: Competitor Comparison, CI/CD Integration, Trend Tracking

### Audit multi-agente completato
- 4 agenti lanciati in parallelo: code-reviewer, security, reviewer, lang-pro
- **38 problemi trovati**: 5 critici, 10 alti, 12 medi, 11 bassi
- 2 SSRF critici (DNS rebinding + redirect chain)
- 20 copie di funzioni scoring duplicate in 4 formatter
- CheckRegistry completamente inerte
- Rate limiter bypassabile in 2 modi diversi
- Report completo salvato nella conversazione

### Round 3 — 5 agenti aggiuntivi (web app, scoring accuracy, mercato, docs, CLI UX)
- Web App: 12 problemi (POST non validato, report "permanente" falso, dati persi in serializzazione)
- Scoring Accuracy: 13 gap (metodo 3 Princeton assente, Bingbot mancante, fallback wildcard, content sottopesato)
- Mercato: 55 repo nel topic, tool commerciali $29-989$/mese fanno monitoring non audit, paper set 2025 conferma earned media
- Docs: TUTTI i file docs/ e ai-context/ usano sintassi legacy `./geo scripts/` — critico
- CLI UX: `llms` rompe pipe su stdout, `--verbose` non operativo, nessun progress durante audit

### Totale cumulativo
- **85 problemi** identificati da 9 agenti in 2 round
- 15 critici, 23 alti, 22 medi, 25 bassi
- 1 bug runtime fixato (URL invalido in geo_audit.py)
- Piano aggiornato in task_plan.md, findings completi in findings.md

### Round 4 — 5 agenti (JSON-LD, llms.txt generator, i18n/legacy, RFC 9309, packaging)
- JSON-LD: template Article manca `image` (obbligatorio Google), `fill_template()` non rileva placeholder residui, Organization.logo stringa vs ImageObject, mancano HowTo/speakable
- llms.txt generator: pattern categorizzazione con falsi positivi (/product, /service), `discover_sitemap` usa HEAD (405 su alcuni server), solo primo Sitemap: da robots.txt, mancano 10+ categorie (FAQ, Pricing, News), SKIP manca /feed/ /author/ /amp/
- i18n: guscio vuoto — `_()` mai usata in nessun file, --lang non ha effetto, mix IT/EN hardcoded
- Legacy scripts/: duplicazione totale, 6 test legacy, promessa rimozione v3.0 non mantenuta, rimozione sicura
- RFC 9309: BOM non strippato nel parser (critico!), longest-match non implementato, limite 500KB assente
- Packaging: GitHub Action injection su inputs.version, Documentation URL probabilmente 404, manca [all] deps, .po inclusi nel pacchetto

### Totale cumulativo
- **~120 problemi** da 14 agenti in 4 round
- Copertura: sicurezza, architettura, test, CI/CD, marketing, web app, scoring, mercato, docs, CLI UX, JSON-LD, llms.txt, i18n, RFC 9309, packaging

### Prossimo step
- Consolidare tutti i findings nel piano
- Decidere priorità di implementazione
- Iniziare fix
