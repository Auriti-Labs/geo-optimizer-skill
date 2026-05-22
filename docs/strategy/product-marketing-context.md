# Product Marketing Context — GeoReady.dev

Documento strategico per guidare pricing, paywall, onboarding, funnel e roadmap.

Ultimo aggiornamento: 2026-05-13

---

## 1. Descrizione sintetica

GeoReady.dev è la versione web di GEO Optimizer: un toolkit che misura e migliora la visibilità dei siti web nei motori di ricerca AI (ChatGPT, Perplexity, Claude, Gemini). Audit quantitativo (score 0-100), fix automatici, monitoraggio nel tempo.

## 2. Descrizione estesa del prodotto

GeoReady.dev combina audit istantaneo, generazione di fix e monitoraggio longitudinale in una singola piattaforma web.

L'audit analizza 8 categorie con 100 punti totali:

| Categoria | Punti | Cosa verifica |
|-----------|-------|---------------|
| Robots.txt | 18 | 27 AI bot in 3 tier (training/search/user), citation bot access |
| llms.txt | 18 | Presenza, struttura H1/blockquote, sezioni, link, profondità, llms-full.txt |
| Schema JSON-LD | 16 | WebSite, Organization, FAQPage, Article, richness ≥5 attributi |
| Meta Tags | 14 | Title, description, canonical, Open Graph completo |
| Content | 12 | H1, statistiche, citazioni esterne, gerarchia heading, liste/tabelle, front-loading |
| Brand & Entity | 10 | Coerenza brand, link Knowledge Graph (Wikipedia/Wikidata/LinkedIn/Crunchbase), about/contact, topic authority |
| Signals | 6 | `<html lang>`, feed RSS/Atom, freshness dateModified |
| AI Discovery | 6 | `.well-known/ai.txt`, `/ai/summary.json`, `/ai/faq.json`, `/ai/service.json` |

Più un **Citability Score** separato (0-100) basato su 47 metodi (Princeton KDD 2024, AutoGEO ICLR 2026).

Funzionalità secondarie:
- **Monitoraggio passivo** (`geo monitor`): snapshot della readiness AI di un dominio senza eseguire audit completi
- **Snapshots AI**: archiviazione e ricerca di risposte AI per verificare se il proprio sito viene citato
- **Citation quality**: scoring della qualità delle citazioni dentro risposte AI archiviate
- **Diff before/after**: confronto quantitativo tra due versioni di una pagina
- **History + regression**: trend storico con alert su regressioni
- **CDN crawler detection**: verifica se Cloudflare/Akamai/Vercel bloccano i bot AI
- **Negative signals**: 8 segnali anti-citazione (CTA overload, popup, thin content, keyword stuffing, missing author, boilerplate alto, mixed signals, link rotti)
- **Prompt injection detection**: 8 pattern di manipolazione (hidden text, invisible Unicode, LLM instructions, HTML comment injection, micro-font, data-attr injection, aria-hidden abuse)
- **Trust Stack Score**: aggregazione su 5 livelli (Technical, Identity, Social, Academic, Consistency) con grade A-F
- **RAG Chunk Readiness**: segmentazione del contenuto per retrieval RAG
- **Content Decay Prediction**: rilevamento decadimento temporale con evergreen score 0-100
- **Platform Citation Profile**: readiness per piattaforma (ChatGPT, Perplexity, Google AI)
- **Factual accuracy**: verifica claim non supportati, contraddizioni, link rotti
- **Coherence analysis**: consistenza terminologica cross-pagina via sitemap
- **Gap analysis**: confronto quantitativo tra due siti con priorità di fix
- **Batch sitemap audit**: fino a 10.000 URL con ordinamento per score

## 3. Differenza tra GEO Optimizer CLI e GeoReady.dev

| Aspetto | GEO Optimizer (CLI) | GeoReady.dev (Web) |
|---------|---------------------|---------------------|
| Licenza | MIT, open-source | Proprietario, SaaS |
| Installazione | `pip install geo-optimizer-skill` | Nessuna installazione |
| Interfaccia | Terminale, 7 formati output (text/json/rich/html/sarif/junit/github) | Browser, UI grafica |
| MCP | Server integrato per Claude/Cursor/Windsurf | API REST (Bearer token) |
| CI/CD | GitHub Action, sarif/junit | Webhook configurabili |
| Monitoraggio | `geo track` locale con SQLite | Dashboard persistente, alert email/webhook |
| Snapshots | `geo snapshots` locale | Archivio cloud con ricerca |
| Storico | `geo history` locale | Dashboard con trend grafici |
| Confronto siti | `geo audit --compare` CLI | Interfaccia visuale side-by-side |
| Fix automatici | `geo fix --apply` genera file | Fix Autopilot con PR GitHub (futuro) |
| Badge | Genera SVG locale | Badge dinamico servito via URL |
| Autenticazione | Nessuna | Bearer token (API), OAuth (web, futuro) |
| Limiti | Nessuno (self-hosted) | Tier-based |

Il CLI è il top-of-funnel: gratuito, open-source, senza limiti. Il valore del SaaS è nella persistenza (monitoraggio, storico, alert) e nell'usabilità (UI vs terminale).

## 4. Problema principale risolto

I siti web sono ottimizzati per Google ma invisibili ai motori di ricerca AI. Quando un utente chiede a ChatGPT, Perplexity o Claude una domanda, questi sistemi citano le fonti che trovano — e la maggior parte dei siti non è configurata per essere trovata e citata. Non esiste uno strumento che misuri quantitativamente questo gap e fornisca fix azionabili.

## 5. Problemi secondari

1. **Nessuna metrica standard per AI visibility**: Non esiste un punteggio universalmente riconosciuto per misurare quanto un sito è "pronto" per essere citato dai LLM. I SEO tool tradizionali (Ahrefs, Semrush, Moz) misurano backlinks e keyword, non citability.
2. **Fix manuali lenti e inconsistenti**: Le checklist GEO generiche dicono "aggiungi llms.txt" ma non verificano se è ben strutturato, non generano il file, e non misurano l'impatto della modifica.
3. **Nessun monitoraggio nel tempo**: Un sito può passare da score 72 a 38 senza che nessuno se ne accorga — nessun tool esistente fa regression detection sulla AI readiness.
4. **CDN e bot blocking non tracciati**: Cloudflare, Akamai e Vercel possono bloccare i bot AI per default. I proprietari del sito non ne sono consapevoli.
5. **Contenuto non citabile**: Anche siti con buon SEO possono avere contenuti strutturati male per la citazione AI — mancanza di statistiche, citazioni, heading gerarchici, RAG chunking.

## 6. Target primari

1. **SEO specialist e manager** (40% del target): Gestiscono 5-50 siti, conoscono il SEO tradizionale, sentono la pressione di "anche AI" dai client. Vogliono metriche quantificabili per giustificare il lavoro ai clienti.
2. **Developer e founder SaaS** (30%): Hanno 1-5 siti/prodotti, sono tecnici, vogliono automatizzare. Il CLI è il loro entry point, il SaaS è per il monitoraggio senza attrito.
3. **Agenzie digitali** (20%): Gestiscono 20-200 siti per clienti multipli. Hanno bisogno di batch audit, confronti, report personalizzabili, e white-label per i clienti finali.

## 7. Target secondari

4. **Content creator e blogger**: 1-2 siti, vogliono capire se il loro contenuto viene citato. Segmento di basso ARPU ma alto volume per il piano Free.
5. **Marketing manager enterprise**: Responsabili di brand grandi, necessitano di audit su domini multipli, monitoraggio continuo, e report per stakeholder interni.
6. **Sviluppatori di tool AI/MCP**: Integrazione via API per pipeline automatizzate. Potenziale revenue indiretto (ecosistema, referral).

## 8. Personas dettagliate

### Persona 1: Marco, SEO Manager (35 anni)

- **Ruolo**: SEO Manager in un'agenzia media (15 persone)
- **Gestisce**: 30 siti di clienti, mix e-commerce e corporate
- **Pain point**: I clienti chiedono "e per ChatGPT?" e non ha una risposta quantificabile. Deve ancora usare spreadsheet e checklist manuali.
- **Cosa cerca**: Un punteggio come PageSpeed Insights ma per AI visibility. Un report da mandare ai clienti.
- **Valore percepito**: Alta — può fatturare il servizio GEO ai clienti.
- **Obiezione principale**: "Non ho tempo per un altro tool, ho già Ahrefs/Semrush."
- **Trigger di conversione**: Un client che chiede esplicitamente visibilità su Perplexity o ChatGPT.

### Persona 2: Valentina, Founder SaaS (32 anni)

- **Ruolo**: CEO e unica persona di marketing di una SaaS B2B
- **Gestisce**: 1 sito, 150 pagine blog
- **Pain point**: Il contenuto tecnico ranka bene su Google ma non viene citato da Perplexity/Claude. Non capisce perché.
- **Cosa cerca**: Fix automatici, non teoria. Vuole azionare e tornare a scrivere codice.
- **Valore percepito**: Medio-alto — se il contenuto viene citato, riduce il CAC.
- **Obiezione principale**: "È davvero diverso dal SEO che faccio già?"
- **Trigger di conversione**: Vedere il proprio sito non citato in una risposta Perplexity per una query rilevante.

### Persona 3: Davide, CTO di Agenzia (40 anni)

- **Ruolo**: CTO, supervisiona audit tecnici per 80+ siti
- **Gestisce**: 80 siti, necessita di batch audit e report riutilizzabili
- **Pain point**: Il team fa audit manuali con checklist. Ogni audit richiede 2-3 ore. Nessuna standardizzazione.
- **Cosa cerca**: Automazione completa, API per integrare nella pipeline CI/CD dei clienti.
- **Valore percepito**: Altissimo — risparmia 10+ ore/settimana al team.
- **Obiezione principale**: "Possiamo farlo con il CLI open-source, perché pagare?"
- **Trigger di conversione**: La necessità di monitoraggio continuo e storico che il CLI non offre centralizzato.

### Persona 4: Chen, Developer Indipendente (28 anni)

- **Ruolo**: Full-stack developer, maintainer di 2-3 progetti open-source con sito docs
- **Gestisce**: 2-3 siti documentazione
- **Pain point**: Vuole che la sua documentazione sia citata quando gli utenti chiedono ai LLM. Non ha budget per tool a pagamento.
- **Cosa cerca**: Il CLI open-source è sufficiente. Potrebbe aggiornare al SaaS per il monitoraggio se il progetto cresce.
- **Valore percepito**: Basso — ha già il CLI gratuito.
- **Trigger di conversione**: Un progetto che diventa commerciale e richiede monitoraggio continuo.

## 9. Use case principali

1. **Audit iniziale**: Un SEO specialist riceve un nuovo cliente. Esegue un audit GeoReady.dev per stabilire il baseline score. Usa il report per giustificare il lavoro GEO nel proposal.
2. **Fix e rivendita**: Un'agenzia esegue l'audit, genera i fix (robots.txt, llms.txt, schema, meta), applica le modifiche, e rivalida. Mostra il delta al cliente.
3. **Monitoraggio continuo**: Un SaaS configura il monitoraggio settimanale. Riceve un alert quando il score scende sotto una soglia — per esempio perché un CDN ha iniziato a bloccare i bot AI.
4. **Competitor benchmark**: Un brand confronta il proprio score con 3-4 competitor per identificare gap specifici (es. "hanno llms.txt con 15 sezioni, noi ne abbiamo 2").
5. **CI/CD gate**: Un team integra il CLI nella GitHub Action. Se il score scende sotto 70 dopo un deploy, il CI fallisce e notifica il team.
6. **Content citability**: Un content writer verifica che i nuovi articoli abbiano statistica, citazioni esterne, e heading gerarchici prima della pubblicazione.

## 10. Differenziazione rispetto ai tool SEO tradizionali

| Aspetto | Ahrefs/Semrush/Moz | GeoReady.dev |
|---------|-------------------|--------------|
| Metrica principale | Domain Authority / DR | GEO Score (0-100) |
| Cosa misura | Backlinks, keyword ranking, traffic | AI citability, bot access, structured data per AI |
| Fix forniti | Suggerimenti SEO generici | Fix specifici per AI (robots.txt per 27 bot, llms.txt, schema per AI) |
| Monitoraggio | Keyword position tracking | Score trend con regression detection |
| Audience | SEO specialist | SEO specialist + developer + founder |
| Prezzo | $99-499/mo | $0-29/mo (o self-hosted gratis) |

**Claim chiave**: I tool SEO dicono se il tuo sito ranka su Google. GeoReady dice se il tuo sito viene citato da ChatGPT.

## 11. Differenziazione rispetto agli audit manuali

| Aspetto | Audit manuale (checklist) | GeoReady.dev |
|---------|--------------------------|--------------|
| Tempo | 2-4 ore per pagina | <10 secondi per pagina |
| Consistenza | Variabile per auditor | Score deterministico e ripetibile |
| Copertura | 10-15 check tipici | 47 metodi citability + 8 categorie audit |
| Aggiornamento | Checklist ferma alle tendenze del momento | Aggiornato con ricerche 2024-2026 (Princeton KDD, AutoGEO ICLR) |
| Monitoraggio | Nessuno | Trend storico con alert |
| Fix | Consigli manuali ("aggiungi llms.txt") | File generati e pronti da applicare |

## 12. Differenziazione rispetto alle checklist GEO generiche

Le checklist GEO (es. "30 cose da fare per GEO") soffrono di tre problemi:

1. **Non misurano**: Dicono "aggiungi llms.txt" ma non verificano se il tuo llms.txt è ben strutturato o se ha 2 sezioni instead of 15.
2. **Non generano**: Dicono "crea uno schema FAQPage" ma non lo generano per te.
3. **Non tracciano**: Non dicono se il tuo score è migliorato o peggiorato nel tempo.

GeoReady risolve tutti e tre: misura (score quantitativo), genera (fix automatici), traccia (monitoraggio + regression).

## 13. Value proposition principale

**GeoReady misura, genera e traccia la visibilità del tuo sito nei motori di ricerca AI — in secondi, non ore.**

Non è un tool SEO. È un tool per chi vuole essere citato da ChatGPT, Perplexity, Claude e Gemini.

## 14. Value proposition per developer

"Integra GEO audit nella tua CI/CD con un comando. Zero configurazione, 47 metodi di citability, fix automatici pronti da deployare. Il CLI è open-source e gratuito — il SaaS è per il monitoraggio continuo."

Punti chiave:
- CLI open-source MIT = zero vendor lock-in per l'audit base
- API REST con Bearer token per integrazione
- GitHub Action ufficiale (`Auriti-Labs/geo-optimizer-skill@v1`)
- Output JSON/SARIF/JUnit per pipeline automatizzate
- MCP server per integrazione con Claude, Cursor, Windsurf

## 15. Value proposition per SEO specialist

"Ottieni un punteggio 0-100 per la AI readiness del tuo sito — come PageSpeed Insights ma per ChatGPT e Perplexity. Genera robots.txt, llms.txt, schema e meta tag ottimizzati per AI con un click. Traccia il progresso nel tempo e dimostra il valore ai clienti."

Punti chiave:
- Score quantificabile da mostrare ai clienti
- Report HTML personalizzabili
- Badge SVG dinamico per siti dei clienti
- Monitoraggio con alert su regressioni
- Confronto competitor side-by-side

## 16. Value proposition per agenzie

"Audita 100+ siti in batch, confronta i risultati, genera report personalizzabili. Risparmia 2-3 ore per audit manuale. Il CLI open-source è la tua dimostrazione, il SaaS è il tuo motore operativo."

Punti chiave:
- Batch audit via sitemap (fino a 10.000 URL)
- API per integrazione nei workflow esistenti
- Report scaricabili e personalizzabili
- Confronto multi-sito
- (Futuro) White-label per i clienti finali

## 17. Value proposition per founder SaaS

"Il tuo contenuto tecnico ranka su Google ma non viene citato da Perplexity. GeoReady identifica esattamente cosa manca e genera i fix. Setup in 2 minuti, risultati misurabili."

Punti chiave:
- Onboarding rapido: inserisci URL, ottieni score e fix
- Fix azionabili, non teoria
- Monitoraggio automatico — non devi ricordarti di ri-auditare
- Prezzo accessibile per singoli founder ($9/mo)

## 18. Obiezioni probabili degli utenti

1. **"Ho già Ahrefs/Semrush, perché mi serve un altro tool?"**
2. **"Posso usare il CLI open-source gratuitamente, perché pagare per il SaaS?"**
3. **"Come fate a sapere cosa ChatGPT cita realmente?"**
4. **"Il GEO score è una vostra metrica, non è standard. Perché dovrei fidarmi?"**
5. **"Il SEO per AI è una moda passeggera?"**
6. **"Il mio sito ranka bene su Google, non mi serve altro."**
7. **"Non ho tempo per ottimizzare per un altro motore di ricerca."**
8. **"I fix generati sono affidabili? Non voglio rompere il sito."**

## 19. Risposte alle obiezioni

### 1. "Ho già Ahrefs/Semrush"

Ahrefs e Semrush misurano backlinks, keyword ranking e traffico Google. Non misurano se i bot AI possono accedere al tuo sito, se hai llms.txt, o se il tuo contenuto è strutturato per essere citato. Sono metriche complementari, non sovrapposte. GeoReady copre un gap che nessun tool SEO esistente copre.

### 2. "Il CLI è gratuito"

Il CLI è eccellente per audit one-off. Il SaaS aggiunge ciò che il CLI non può dare: monitoraggio persistente (non SQLite locale), alert su regressioni, trend storici centralizzati, confronti multi-sito, e UI per team non-tecnici. Se ti basta il CLI, usalo — è MIT, senza limiti.

### 3. "Come fate a sapere cosa ChatGPT cita?"

Non simuliamo risposte AI. Misuriamo i fattori che la ricerca (Princeton KDD 2024, AutoGEO ICLR 2026) ha dimostrato correlare con la citazione: struttura del contenuto, statistiche, citazioni esterne, meta tag, schema, robots.txt, llms.txt. Il Citability Score è basato su 47 metodi quantitativi, non opinioni.

### 4. "Il GEO score non è standard"

Nessuna metrica è "standard" finché non lo diventa. PageSpeed non era standard quando Google l'ha introdotto. Il nostro score è trasparente (pesi pubblici in `config.py`, metodologia documentata), riproducibile (stesso URL = stesso score), e basato su ricerca peer-reviewed. Il codice è open-source — chiunque può verificare come funziona.

### 5. "È una moda passeggera"

Il traffico AI è cresciuto dal 2% al 15% del traffico web in 18 mesi (dati 2024-2026). ChatGPT ha 400M+ utenti settimanali. Perplexity è valutato $9B. Non è una moda — è un cambiamento strutturale nel modo in cui le persone trovano informazioni.

### 6. "Ranko bene su Google"

Ottimo. Ma Google e ChatGPT usano segnali diversi. Un sito può essere #1 su Google e invisibile su Perplexity perché il CDN blocca i bot AI, manca llms.txt, o il contenuto non è strutturato per la citazione. Sono due ottimizzazioni diverse, non una.

### 7. "Non ho tempo"

Audit completo in <10 secondi. Fix generati in un click. Monitoraggio automatico settimanale — zero manutenzione. Il tempo lo investi una volta per il setup, poi è automatizzato.

### 8. "I fix sono affidabili?"

I fix sono basati sulle specifiche ufficiali (robots.txt, schema.org, llms.txt spec, Open Graph). Ogni fix è revisionabile prima dell'applicazione. Il CLI genera file che puoi ispezionare, non patch binari. Il codice è open-source e auditabile.

## 20. Funzionalità candidate per il piano Free

- **3 audit/mese** (homepage singola)
- Score completo 0-100 con breakdown per categoria
- Raccomandazioni testuali (senza fix generati)
- Badge SVG dinamico (con watermark "Free")
- Citability Score (47 metodi, singola pagina)
- Confronto fino a 2 siti
- Accesso al CLI open-source (sempre gratuito, sempre completo)

Strategia: il Free tier deve essere sufficiente per dimostrare valore ma insufficiente per uso professionale. 3 audit/mese costringe l'upgrade per chi gestisce multipli siti o ha bisogno di monitoraggio.

## 21. Funzionalità candidate per il piano Pro ($9/mese)

- **20 URL monitorate** con audit settimanale automatico
- Alert email su regressioni (soglia configurabile)
- Fix automatici generati (robots.txt, llms.txt, schema, meta)
- Citability Score per tutte le URL monitorate
- Confronto fino a 5 siti
- Storico score con trend grafici (fino a 12 mesi)
- Badge SVG senza watermark
- AI Discovery check
- Negative signals check
- Trust Stack Score
- Export report HTML/PDF
- API access (rate-limited: 100 req/ora)

Strategia: il Pro è il piano "sweet spot" — copre l'85% degli utenti. Il valore principale è il monitoraggio automatico + alert, che risolve il problema "devo ricordarmi di ri-auditare".

## 22. Funzionalità candidate per il piano Studio / Agency ($29/mese)

- **100 URL monitorate** con audit giornaliero
- Tutto del Pro, più:
- Batch audit via sitemap (fino a 10.000 URL)
- Competitor intelligence (confronto con fino a 10 competitor)
- Content Decay Prediction
- Platform Citation Profile (per-platform readiness)
- RAG Chunk Readiness
- Factual Accuracy audit
- Coherence analysis cross-pagina
- API access aumentato (1000 req/ora)
- Report personalizzabili con logo agenzia
- (Futuro) Fix Autopilot con PR GitHub automatiche
- (Futuro) White-label badge e report

Strategia: l'Agency paga per volume (100 URL) e funzionalità avanzate (batch, competitor, content decay). Il prezzo è competitivo rispetto a $49-295 dei competitor.

## 23. Funzionalità candidate per il piano Enterprise ($99/mese o custom)

- **URL illimitate** con audit frequenza personalizzabile
- Tutto dello Studio, più:
- API access illimitato
- Slack/Teams webhook per alert
- SSO/SAML
- SLA garantito
- Account manager dedicato
- Priorità su feature request
- Deployment self-hosted assistito
- Integrazione CI/CD avanzata (GitLab, Jenkins, CircleCI)
- Dati esportabili (CSV, JSON, SARIF)
- (Futuro) White-label completo

Strategia: Enterprise è per aziende grandi che hanno requisiti di compliance, volume, e supporto. Il prezzo custom riflette il valore del supporto dedicato e della personalizzazione.

## 24. Claim consigliati

- "Misura la visibilità del tuo sito per ChatGPT, Perplexity, Claude e Gemini."
- "Audit GEO in 10 secondi. Score 0-100 basato su 47 metodi di ricerca."
- "Il SEO ti fa rankare su Google. Il GEO ti fa citare dalle AI."
- "Da score a fix in un click. robots.txt, llms.txt, schema, meta — generati per te."
- "Non è SEO. È GEO — l'ottimizzazione per i motori di ricerca AI."
- "Open-source audit, monitoraggio SaaS. Inizia gratis."
- "Il tuo sito è visibile per Google. Ma lo è per ChatGPT?"
- "47 metodi. 100 punti. 0 ipotesi."

## 25. Claim da evitare

- ❌ "La soluzione definitiva per la AI visibility" — troppo vaga, non credibile
- ❌ "Garantiamo che ChatGPT citerà il tuo sito" — falso promesso, impossibile garantire
- ❌ "Il primo tool per GEO" — non verificabile, probabilmente falso
- ❌ "Basato su AI" — non è un vantaggio differenziatore qui
- ❌ "Rivoluzionario" — vuoto, non dice nulla
- ❌ "Sostituisce il tuo tool SEO" — falso, è complementare
- ❌ "Ottimizzato per LLM" — ambiguo, può suggerire prompt injection
- ❌ Qualsiasi claim di percentuale di aumento traffico senza dati verificabili

## 26. Linguaggio consigliato

| Dire | Evitare | Perché |
|------|---------|--------|
| AI visibility | AI optimization | "Optimization" suona come manipolazione |
| Citability score | AI readiness | "Readiness" è vago; citability è specifico e misurabile |
| AI search engines | LLMs | Il pubblico business capisce "AI search" meglio di "LLM" |
| Score 0-100 | Rating | Score è quantitativo, rating è qualitativo |
| Fix automatici | Auto-optimization | "Fix" è chiaro e limitato; "auto-optimization" suona come black box |
| Monitoraggio | Tracking | Monitoraggio implica osservazione attiva; tracking è passivo |
| Metrica | Metric | Italiano quando possibile |
| Audit | Analisi | Audit è il termine tecnico standard |
| Regressione | Peggioramento | Regressione è più preciso e tecnico |
| Bot AI | Crawler AI | "Bot" è il termine usato in robots.txt |
| Schema strutturato | Dati strutturati | Entrambi corretti; usare "schema JSON-LD" per specificità |

## 27. Linguaggio da evitare

- "Disruptive", "game-changer", "paradigm shift" — vuoto e non credibile
- "AI-powered" — non è un differenziatore qui
- "Next-generation" — data di scadenza breve
- "Hack", "trick", "gaming" — suggerisce manipolazione, non ottimizzazione legittima
- "Guaranteed", "proven" — claim che non puoi dimostrare
- Linguaggio aggressivo o urgency-based ("Don't miss out!", "Act now!")
- Comparazioni dirette con competitor nominati ("Better than Ahrefs") — mantenere la comparazione sul piano dei fatti e delle feature
- Gerghi SEO avanzati senza spiegazione (no "canonicalization", "hreflang", "crawl budget" senza contesto)

## 28. North Star Metric consigliata

**Numero di URL monitorate attivamente (weekly active monitored URLs)**

Perché questa metrica e non altre:

| Metrica | Problema |
|---------|----------|
| Audit eseguiti | Alta ma non indica engagement — l'utente può auditare e non tornare |
| Utenti registrati | Vanity metric — non indica valore ricevuto |
| MRR | Lagging indicator — arriva dopo il valore |
| NPS | Importante ma survey-based, non comportamentale |

URL monitorate attivamente indica che l'utente ha:
1. Configurato un URL per il monitoraggio ricorrente
2. Non ha cancellato il monitoraggio
3. Sta ricevendo valore continuo (altrimenti rimuove l'URL)

Questa metrica allinea incentivi: più URL monitorati = più valore per l'utente = più MRR.

### Metriche secondarie

- **Audit-to-monitor conversion rate**: % di utenti Free che configurano almeno un URL monitorato (indicatore di attivazione)
- **Weekly score improvement**: media del delta score per URL monitorato (indicatore di valore)
- **Churn by tier**: tasso di abbandono per piano (indicatore di retention)
- **API calls per account**: utilizzo API per sviluppatori (indicatore di engagement nel Pro/Studio)

## 29. Eventi principali da tracciare

### Onboarding

| Evento | Descrizione | Proprietà |
|--------|-------------|-----------|
| `geo_signup` | Registrazione completata | tier, source |
| `geo_first_audit` | Primo audit eseguito | url, score, duration_ms |
| `geo_first_fix_viewed` | Primo fix visualizzato | url, fix_type |
| `geo_first_monitor_setup` | Primo URL monitorato | url, frequency |

### Engagement

| Evento | Descrizione | Proprietà |
|--------|-------------|-----------|
| `geo_audit_run` | Audit eseguito | url, score, categories, duration_ms, source (web/api/cli) |
| `geo_score_improved` | Score migliorato | url, old_score, new_score, delta |
| `geo_score_regressed` | Score regredito | url, old_score, new_score, delta, categories_regressed |
| `geo_fix_generated` | Fix generato | url, fix_type (robots/llms/schema/meta) |
| `geo_fix_applied` | Fix applicato | url, fix_type, method (manual/autopilot) |
| `geo_badge_generated` | Badge SVG generato | url, score, tier |
| `geo_compare_run` | Confronto eseguito | urls, scores |
| `geo_monitor_check` | Monitoraggio eseguito | url, score, alert_triggered |

### Conversione

| Evento | Descrizione | Proprietà |
|--------|-------------|-----------|
| `geo_paywall_hit` | Utente raggiunge limite Free | feature, limit |
| `geo_upgrade_started` | Inizio checkout | from_tier, to_tier |
| `geo_upgrade_completed` | Checkout completato | from_tier, to_tier, mrr |
| `geo_downgrade` | Passaggio a piano inferiore | from_tier, to_tier, reason |

### Retention

| Evento | Descrizione | Proprietà |
|--------|-------------|-----------|
| `geo_alert_received` | Alert ricevuto | url, type, score_delta |
| `geo_alert_clicked` | Alert clickato | url, type |
| `geo_report_downloaded` | Report scaricato | url, format (html/pdf) |
| `geo_api_call` | Chiamata API | endpoint, status_code, duration_ms |

## 30. Raccomandazione finale sulla monetizzazione

### Modello: Freemium con 4 tier

| Tier | Prezzo | Posizionamento |
|------|--------|----------------|
| Free | $0 | Top-of-funnel, dimostra valore |
| Pro | $9/mo | Individuali e piccoli team |
| Studio | $29/mo | Agenzie e professionisti |
| Enterprise | $99/mo o custom | Grandi organizzazioni |

### Sequenza di implementazione

1. **Fase 1 (ora)**: Free tier con 3 audit/mese + CLI open-source. Raccogliere dati di utilizzo, validare value proposition, costruire audience.

2. **Fase 2 (mese 1-2)**: Pro tier con monitoraggio settimanale + alert + fix generati. Questa è la funzionalità con il rapporto sforzo/valore più alto — è la ragione principale per pagare.

3. **Fase 3 (mese 3-4)**: Studio tier con batch sitemap, competitor intelligence, content decay, report personalizzabili. Questo sblocca il mercato agenzie.

4. **Fase 4 (mese 5+)**: Enterprise tier con API illimitata, SSO, SLA. Solo quando ci sono richieste esplicite.

### Non costruire (per ora)

- **White-label**: Troppo presto, aggiunge complessità prima del product-market fit.
- **WordPress plugin**: Audience diversa, diluisce il focus.
- **SDK per AI assistant**: Nice-to-have, non genera revenue.
- **Marketplace di fix**: Complessità elevata, bassa domanda.

### Il CLI open-source come vantaggio competitivo

Il CLI open-source non è una minaccia per il SaaS — è il funnel di acquisizione più potente:

1. **Scoperta**: Gli sviluppatori trovano il CLI su PyPI/GitHub, lo provano, ottengono valore.
2. **Adozione**: Lo integrano nella CI/CD, lo consigliano al team.
3. **Limite**: Il CLI non ha monitoraggio persistente, alert, storico centralizzato, o UI.
4. **Conversione**: Quando serve monitoraggio, l'upgrade al SaaS è naturale.

Non limitare mai il CLI. Più persone lo usano, più persone scoprono GeoReady.dev.

### Pricing psychology

- $9/mo è sotto la soglia dei $10 dove le persone valutano l'acquisto come "inexpensive" vs "cheap".
- $29/mo è il prezzo medio per tool professionali (Ahrefs Lite era $99, Semrush Guru è $449 — siamo il 10-30%).
- $99/mo per Enterprise è competitivo rispetto a $245-295 dei competitor diretti (Peec AI, AthenaHQ).
- Il Free tier con 3 audit/mese è sufficiente per dimostrare valore ma insufficiente per uso professionale — spinge al Pro.

### Metrica di successo a 6 mesi

- **1.000 URL monitorate attivamente** (Pro + Studio + Enterprise)
- **5.000 audit/mese** su tutto il platform (Free + paid)
- **10% audit-to-monitor conversion rate**
- **$2.000 MRR** (circa 150 utenti Pro + 20 Studio)

---

*Questo documento guida pricing, paywall, onboarding e roadmap. Aggiornare quando i dati di utilizzo validano o invalidano le assunzioni.*