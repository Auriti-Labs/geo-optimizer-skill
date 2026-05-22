# Product Marketing Context — GeoReady.dev

*Versione: 2.0 — Aggiornato: 2026-05-13*
*Questo documento è la base strategica per tutte le skill marketing, CRO, SEO, pricing, onboarding e launch strategy.*

---

## 1. Descrizione sintetica del prodotto

GeoReady.dev è la piattaforma web di GEO Optimizer: uno strumento di audit, fix e monitoraggio per la visibilità AI di un sito web. Misura quanto un sito è leggibile, comprensibile e citabile dai motori di risposta AI — ChatGPT, Perplexity, Claude, Gemini, Google AI Overviews — e genera i file di correzione necessari.

**Tagline operativa:** *Misura quanto il tuo sito è visibile all'AI. Correggi quello che manca. Monitora nel tempo.*

---

## 2. Descrizione estesa del prodotto

GEO Optimizer (v4.10.4, MIT) è un toolkit Python open-source accessibile via CLI, API REST e interfaccia web su geoready.dev. L'engine di audit valuta un sito su **8 categorie** per un totale di **100 punti**:

| Categoria | Punti | Cosa valuta |
|-----------|-------|-------------|
| Robots.txt | 18 | 27 AI bot su 3 tier (training, search, user). I citation bot sono esplicitamente abilitati? |
| llms.txt | 18 | Presenza, struttura H1, blockquote, sezioni, link, profondità. Companion llms-full.txt? |
| Schema JSON-LD | 16 | WebSite, Organization, FAQPage, Article. Ricchezza schema (5+ attributi)? |
| Meta Tags | 14 | Titolo, descrizione, canonical, Open Graph completo |
| Content | 12 | H1, dati numerici, link esterni, gerarchia heading, liste/tabelle, front-loading |
| Brand & Entity | 10 | Coerenza brand, Knowledge Graph (Wikipedia/Wikidata/LinkedIn), about page, geo identity, topic authority |
| Signals | 6 | `<html lang>`, RSS/Atom, dateModified freshness |
| AI Discovery | 6 | `.well-known/ai.txt`, `/ai/summary.json`, `/ai/faq.json`, `/ai/service.json` |

**Bande di punteggio:** 86-100 Excellent · 68-85 Good · 36-67 Foundation · 0-35 Critical

Oltre al punteggio principale, il prodotto include analisi avanzate non incluse nel punteggio ma rilevanti per diagnosi approfondita:

- **Citability Score (0-100):** 47 metodi da Princeton KDD 2024 — quotazioni, statistiche, fluency, cite sources, 43 altri
- **Trust Stack Score (A-F):** aggregazione 5 layer — Technical, Identity, Social, Academic, Consistency
- **Prompt Injection Detection:** 8 pattern di manipolazione AI nel contenuto
- **RAG Chunk Readiness:** ottimizzazione del contenuto per retrieval AI
- **Content Decay Prediction:** individuazione di contenuto con dati temporali/statistici obsoleti
- **Platform Citation Profile:** punteggi per-platform — ChatGPT, Perplexity, Google AI
- **Negative Signal Detection:** 8 segnali anti-citazione — popup, thin content, keyword stuffing, CTA excessivi
- **CDN Crawler Access:** verifica se Cloudflare/Akamai/Vercel bloccano i bot AI

**Comandi principali:**
- `geo audit` — audit completo con punteggio e raccomandazioni
- `geo fix --apply` — generazione automatica di robots.txt, llms.txt, schema, meta
- `geo compare` — confronto tra più siti con gap analysis
- `geo monitor` — snapshot passivo AI visibility
- `geo snapshots` — archivio risposte AI con citation quality scoring
- `geo history` / `geo track` — storico punteggi e report HTML di trend
- `geo llms` — generazione llms.txt da sitemap
- `geo schema` — generazione schema JSON-LD

**Formati di output:** testo, JSON, HTML, SARIF (GitHub Security), JUnit (CI/CD), GitHub Annotations.

**MCP Server:** 12 tool + 5 risorse per Claude, Cursor, Windsurf e qualsiasi client MCP.

**Fondamento scientifico:** Princeton KDD 2024 (9 metodi su 10k query), AutoGEO ICLR 2026 (+50.99% sul baseline), C-SEO Bench 2025 (l'infrastruttura tecnica batte il content rewriting).

---

## 3. Problema principale che il prodotto risolve

**I motori di risposta AI (ChatGPT, Perplexity, Gemini, Claude) citano le fonti. Se un sito non è ottimizzato per essere letto, compreso e citato da questi sistemi, è invisibile — indipendentemente dal suo posizionamento su Google.**

Il problema è strutturale, non di contenuto: un sito può scrivere testi eccellenti e posizionarsi in prima pagina su Google, eppure non apparire mai nelle risposte AI perché manca il file llms.txt, i bot di citazione sono bloccati in robots.txt, lo schema JSON-LD è assente o malformato, o i segnali di entità brand non sono coerenti.

**Conseguenza concreta:** un competitor con contenuto inferiore ma struttura tecnica corretta appare nelle risposte di Perplexity. Il sito meglio scritto non appare. Non c'è modo di saperlo senza misurarlo.

---

## 4. Problemi secondari

**P2 — Mancanza di baseline e metriche**
Non esiste uno standard di riferimento condiviso per la visibilità AI. GEO Optimizer definisce un punteggio 0-100 con pesi derivati dalla ricerca pubblica, rendendo possibile confrontare siti e misurare il miglioramento nel tempo.

**P3 — Generazione manuale di file tecnici complessa**
Scrivere un llms.txt corretto, configurare ai.txt, generare uno schema FAQPage o un WebSite schema richiede conoscenza tecnica e ore di lavoro. `geo fix --apply` li genera automaticamente in secondi.

**P4 — Regressioni invisibili**
Una modifica al CMS, un aggiornamento del tema WordPress, un redirect cambiato: possono abbassare il punteggio GEO senza che nessuno se ne accorga. Senza monitoring attivo, la regressione viene scoperta solo quando il traffico AI cala.

**P5 — Nessun confronto con i competitor**
Chi appare nelle risposte AI al posto mio? Cosa hanno di diverso? `geo compare` + gap analysis risponde a questa domanda con dati concreti, non supposizioni.

**P6 — Manipolazione del contenuto da parte di attori terzi**
Siti con testo nascosto, istruzioni LLM iniettate, Unicode invisibile possono alterare il modo in cui l'AI interpreta il contenuto. Il Prompt Injection Detector identifica questi pattern prima che causino danni reputazionali.

**P7 — Bot AI bloccati da CDN senza saperlo**
Cloudflare, Akamai e Vercel possono bloccare GPTBot, ClaudeBot e PerplexityBot per default. Il CDN Crawler Access check lo rileva con una singola analisi.

---

## 5. Target primari

Ordinati per probabilità di conversione a pagamento nella fase attuale del mercato.

### T1 — Agenzie SEO e digitali (5-30 persone)
Già pagano strumenti SEO (€100-200/mese/tool). I clienti chiedono visibilità AI. Non hanno processi GEO formalizzati. Vogliono uno strumento che produca report da consegnare, non un altro CLI da imparare.

**Trigger di acquisto:** il cliente chiede "siamo su ChatGPT?" e l'agenzia non ha una risposta.

### T2 — Consulenti WordPress e web freelance
Ottimizzano siti per SEO classica. Ogni sito che consegnano ha un gap GEO non dichiarato. Vogliono aggiungere un deliverable senza aumentare il tempo di lavoro.

**Trigger di acquisto:** un cliente si lamenta che non appare nelle risposte AI dopo un rifacimento del sito.

### T3 — SEO specialist freelance
Abituati a pagare tool. Cercano attivamente soluzioni GEO perché il mercato li sta chiedendo. Alta affinità con il formato audit + score.

**Trigger di acquisto:** deve proporre a un cliente un'analisi GEO e non ha uno strumento consolidato.

---

## 6. Target secondari

### T4 — Founder SaaS e product manager con landing page pubbliche
Investono in content marketing. Non vogliono gestire un CLI ma vogliono sapere se il loro sito è citabile. Probabilmente pagano un piano base, non monitoring continuo.

### T5 — Developer che integrano audit GEO in pipeline CI/CD
Usano già il CLI open source. Convertibili su feature cloud che il locale non può dare: dashboard, storico, alert, API key.

### T6 — Responsabili marketing di aziende con forte presenza content
Blog aziendali, knowledge base, documentazione prodotto. Hanno contenuto di qualità ma infrastruttura tecnica AI non ottimizzata. Interessati al batch audit su più URL.

### T7 — Professionisti che propongono GEO come nuovo servizio
Stanno costruendo un'offerta consulenziale su AI Search / AEO / GEO. Cercano credibilità e strumentazione. GeoReady.dev è il tool che supporta quella proposta.

---

## 7. Personas dettagliate

### Persona A — "Luca" · SEO Specialist Freelance · 32 anni
**Contesto:** 5 anni di esperienza SEO. Usa Ahrefs + Screaming Frog + Google Search Console. Ha 8-12 clienti attivi. Negli ultimi 6 mesi riceve domande su AI search da 3-4 clienti.
**Obiettivo:** avere uno strumento GEO credibile da aggiungere al proprio stack senza imparare Python.
**Frustrazione:** i blog spiegano la teoria, nessuno dà uno strumento concreto. Le checklist manuali richiedono 2-3 ore per sito.
**Come usa il prodotto:** audit web per assessment iniziale del cliente, PDF da allegare alla proposta, piano Pro per monitorare i siti attivi.
**Barriera principale:** "Non so se GEO vale davvero il tempo di un cliente."
**Messaggio chiave:** *Porta dati alla conversazione. Un punteggio GEO è più convincente di una spiegazione verbale.*

---

### Persona B — "Martina" · Titolare agenzia digitale · 38 anni
**Contesto:** Gestisce un'agenzia di 8 persone. Mix di SEO, social, web design. Ha 20+ clienti attivi. Almeno 5 le hanno chiesto di "ottimizzare per ChatGPT" nell'ultimo anno.
**Obiettivo:** standardizzare un processo GEO per tutta l'agenzia senza assumere personale specializzato.
**Frustrazione:** ogni audit è manuale e diverso. Non ha un framework riproducibile. Non riesce a fare upsell GEO perché non ha un deliverable concreto.
**Come usa il prodotto:** batch audit su tutti i clienti, template report brandizzato, monitoring con alert per identificare regressioni post-aggiornamento sito.
**Barriera principale:** "Un altro strumento da pagare e da far adottare al team."
**Messaggio chiave:** *Un audit GEO in 30 secondi per sito. Report PDF pronto da consegnare. Nessun training necessario.*

---

### Persona C — "Andrea" · Sviluppatore full-stack · 27 anni
**Contesto:** Lavora come indie developer. Ha un SaaS in fase early con landing page e blog. Usa Python regolarmente. Ha già installato e provato il CLI.
**Obiettivo:** assicurarsi che il suo sito sia citabile prima del lancio pubblico. Vuole anche integrare il check nella pipeline CI/CD.
**Frustrazione:** capisce il prodotto, ma non ha tempo di costruire un sistema di monitoring locale. Vuole delegar la parte di infrastruttura.
**Come usa il prodotto:** CLI per sviluppo locale + SARIF per GitHub Actions + piano Starter per monitoring URL post-lancio.
**Barriera principale:** "Posso fare tutto con il CLI gratis — perché pagare?"
**Messaggio chiave:** *Il CLI audita. La piattaforma monitora, salva lo storico e ti avvisa quando qualcosa cambia.*

---

### Persona D — "Sara" · Consulente WordPress · 35 anni
**Contesto:** 9 anni di esperienza WordPress. Fa siti per PMI, professionisti, ristoranti, studi legali. Non è tecnica su Python ma conosce bene il CMS.
**Obiettivo:** aggiungere un check GEO al processo di consegna senza dover imparare un nuovo stack.
**Frustrazione:** ha letto di llms.txt su un blog ma non sa come generarlo correttamente. Teme di consegnare siti che "non funzionano per AI".
**Come usa il prodotto:** web app per audit rapido prima della consegna, `geo fix` per generare i file mancanti, report HTML da allegare alla documentazione del progetto.
**Barriera principale:** "Non so se il cliente capisce il valore di questa cosa."
**Messaggio chiave:** *Genera llms.txt, robots.txt AI-ready e schema in 30 secondi. Consegna un sito che funziona anche per AI search.*

---

## 8. Use case principali

**UC1 — Pre-lancio audit**
Un developer o fondatore audita il proprio sito prima del go-live pubblico. Identifica i gap critici (robots.txt, llms.txt mancante, schema assente) e li corregge prima che il sito venga indicizzato dai bot AI.

**UC2 — Assessment cliente per agenzia**
Un'agenzia o consulente audita il sito di un potenziale cliente come parte di una proposta commerciale. Il punteggio GEO diventa un deliverable concreto che giustifica il progetto di ottimizzazione.

**UC3 — Monitoring post-aggiornamento**
Un sito in produzione viene aggiornato (nuovo tema, migrazione CMS, aggiornamento plugin). Il monitoring automatico rileva se il punteggio GEO è regredito e invia un alert.

**UC4 — Confronto con competitor**
Un SEO specialist usa `geo compare` per capire perché un competitor appare nelle risposte di Perplexity e il proprio cliente no. La gap analysis ordina le correzioni per impatto.

**UC5 — Generazione file tecnici**
Un consulente WordPress deve aggiungere llms.txt, ai.txt e schema FAQPage a un sito senza scrivere il codice a mano. `geo fix --apply` genera i file corretti in secondi.

**UC6 — CI/CD integration**
Un team di sviluppo integra il check GEO nella pipeline GitHub Actions. Se il punteggio scende sotto 70 su una PR, il deploy viene bloccato automaticamente (exit code non zero + SARIF nel Security tab).

**UC7 — Batch audit su portfolio clienti**
Un'agenzia con 20+ clienti vuole un report mensile di tutti i punteggi GEO. Batch audit via CSV, export consolidato, individuazione dei clienti con regressioni critiche.

**UC8 — Verifica antecedente alla consegna WordPress**
Prima di chiudere un progetto, il consulente esegue l'audit e allega il report HTML come documentazione di consegna. Il cliente vede il punteggio e i file generati.

---

## 9. Differenziazione rispetto ai tool SEO tradizionali

| Dimensione | Ahrefs / Semrush / Moz | GeoReady.dev |
|------------|------------------------|--------------|
| Focus | Ranking su Google | Citabilità su AI search engines |
| llms.txt audit | Assente | Presente con scoring dettagliato |
| robots.txt AI bot | Solo check base | 27 AI bot su 3 tier con scoring granulare |
| Schema per AI | Validazione generica | Scoring per tipo (FAQPage, Article, Organization) |
| AI Discovery endpoints | Assente | ai.txt, summary.json, faq.json, service.json |
| Citability Score | Assente | 47 metodi da ricerca accademica |
| Prompt Injection Detection | Assente | 8 pattern rilevati con fonte UC Berkeley EMNLP 2024 |
| Trust Stack Score | Assente | 5 layer, grade A-F |
| MCP integration | Assente | 12 tool + 5 risorse |
| Fondamento scientifico | Non dichiarato | Princeton KDD 2024, AutoGEO ICLR 2026 con citazione |

I tool SEO tradizionali ottimizzano per i crawler Google. GeoReady ottimizza per i crawler dei sistemi di risposta AI. Sono canali diversi con segnali tecnici diversi.

---

## 10. Differenziazione rispetto agli audit manuali

Un audit manuale su llms.txt / robots.txt / schema / meta richiede 2-4 ore per sito, conoscenza dei 27 bot AI rilevanti, aggiornamento manuale ogni volta che cambiano le specifiche dei bot, e zero riproducibilità tra un auditor e l'altro.

GeoReady.dev:
- Audit completato in meno di 30 secondi
- Punteggio deterministico e riproducibile (stessa URL = stesso score)
- Scoring ponderato con pesi derivati dalla ricerca — non opinioni
- Generazione automatica dei file corretti — non solo segnalazione del problema
- Storico e confronto nel tempo — impossibile manualmente senza infrastruttura dedicata
- Confronto competitor in un'unica run — richiede ore se fatto manualmente

---

## 11. Differenziazione rispetto a semplici checklist GEO

Le checklist GEO circolanti sui blog (SE Ranking, Zyppy, ahrefs.com/blog) elencano cosa fare senza:
- Misurare se è stato fatto correttamente
- Pesare l'importanza relativa di ogni elemento
- Rilevare se i bot AI sono effettivamente bloccati (robots.txt può essere presente ma sbagliato)
- Generare i file corretti
- Rilevare regressioni nel tempo
- Confrontare con i competitor
- Rilevare prompt injection o Trust Stack compromessi

Una checklist dice "aggiungi llms.txt". GeoReady.dev dice "il tuo llms.txt manca del blockquote (−1pt), ha sezioni ma nessun link esterno (−2pt), punteggio sezione: 9/18 — ecco il file corretto."

---

## 12. Motivi per cui un utente dovrebbe fidarsi del prodotto

**12.1 — Fondamento scientifico dichiarato e verificabile**
Ogni segnale ha un'origine citata: Princeton KDD 2024 (arxiv.org/abs/2311.09735), AutoGEO ICLR 2026 (arxiv.org/abs/2510.11438), C-SEO Bench 2025. Non "best practice" anonime.

**12.2 — Scoring completamente trasparente**
I pesi di ogni categoria sono pubblici in `models/config.py`. Chiunque può verificare perché un sito riceve 14/18 su llms.txt invece di 18/18.

**12.3 — Open source MIT**
Il codice è pubblico. Non ci sono black box. Chi non si fida del punteggio può leggere l'algoritmo.

**12.4 — Trazione organica misurabile**
407 GitHub stars, 4.000 download/mese su PyPI, 1.600+ audit eseguiti. Numeri dichiarati come snapshot di maggio 2026, non live — onestà sulla natura del dato.

**12.5 — Nessuna promessa di ranking**
GeoReady.dev non promette che il tuo sito apparirà su ChatGPT. Promette di misurare i segnali tecnici che i sistemi AI usano per decidere cosa citare. La differenza è sostanziale.

**12.6 — Versione CLI open source usabile senza account**
Chi vuole verificare il tool prima di fidarsi può installarlo con `pip install geo-optimizer-skill` e testarlo localmente. Nessun lock-in iniziale.

---

## 13. Obiezioni probabili degli utenti

**O1 — "Il GEO è ancora troppo nuovo per investirci"**
**O2 — "Non so se ChatGPT guarda davvero questi segnali"**
**O3 — "Semrush lo aggiungerà tra 6 mesi e avrò già lo strumento"**
**O4 — "Posso fare queste cose manualmente con una checklist"**
**O5 — "Non voglio un altro abbonamento mensile"**
**O6 — "Il CLI è gratis — perché dovrei pagare la web app?"**
**O7 — "I miei clienti non capiscono cosa sia il GEO"**
**O8 — "Non so se il punteggio riflette davvero come funzionano questi sistemi AI"**

---

## 14. Risposte alle obiezioni

**O1 — "È troppo nuovo"**
Perplexity supera i 100 milioni di query al giorno. Google AI Overviews è in rollout su miliardi di ricerche. Le citazioni AI già generano traffico misurabile. Chi ottimizza oggi ha un vantaggio su chi aspetta che diventi mainstream.

**O2 — "Non so se ChatGPT guarda questi segnali"**
I paper accademici (Princeton KDD, AutoGEO) testano queste variabili su 10.000+ query reali e misurano l'impatto sulla frequenza di citazione. Non sono ipotesi — sono risultati empirici. Il codice implementa esattamente quei test.

**O3 — "Semrush lo farà presto"**
I tool SEO generalisti aggiungeranno feature GEO come bolt-on. GeoReady.dev è costruito attorno al problema GEO da zero. La profondità di analisi (47 metodi citability, prompt injection, Trust Stack, RAG readiness) non è replicabile con un tab aggiuntivo.

**O4 — "Posso usare una checklist"**
Una checklist segnala cosa fare. GeoReady.dev misura se è stato fatto correttamente, genera i file corretti e notifica se regredisce. La differenza è tra un piano e un sistema.

**O5 — "Un altro abbonamento"**
Il piano base (monitoring di 5 URL) costa meno di un'ora del tuo tempo se evita una regressione non rilevata. Il piano Pro copre 20 URL — meno di un singolo tool SEO che già paghi.

**O6 — "Il CLI è gratis"**
Il CLI audita un URL alla volta, in locale, senza storico cloud, senza alerting, senza dashboard, senza report PDF da consegnare al cliente. La web app aggiunge lo strato di continuità e collaborazione che il CLI non può dare.

**O7 — "I clienti non capiscono il GEO"**
Un punteggio 100/100 è comprensibile da chiunque. Il report PDF con score visivo e lista di fix è un deliverable concreto, non un'analisi accademica. Il cliente non deve capire il GEO — deve capire che qualcosa manca e che tu lo hai corretto.

**O8 — "Non so se il punteggio è accurato"**
I pesi sono pubblici, la metodologia è citata, il codice è open source. Se hai dubbi, puoi leggere l'algoritmo. Nessun competitor può dire lo stesso.

---

## 15. Linguaggio consigliato

**Termini da usare:**
- *AI search engine* (non "motore AI" in modo generico)
- *Citabilità* / *citability* (il concetto centrale del prodotto)
- *Visibilità AI* (non "ranking AI" — non esiste un ranking in senso Google)
- *Leggibilità AI* (capacità tecnica di essere processato dai crawler)
- *GEO score* / *punteggio GEO*
- *llms.txt*, *ai.txt*, *schema JSON-LD* (nomi tecnici precisi)
- *Segnali tecnici* (non "algoritmo" — troppo vago)
- *Audit GEO*, *analisi GEO*, *fix GEO*
- *Monitoraggio*, *storico*, *regressione*
- *Motori di risposta AI* (più preciso di "AI search")

**Frasi efficaci:**
- "Misura quanto il tuo sito è citabile dai sistemi AI"
- "Genera i file tecnici che i bot AI cercano"
- "Monitora il punteggio nel tempo e ricevi alert sulle regressioni"
- "Basato su ricerca peer-reviewed — non best practice anonime"
- "Il tuo competitor su Perplexity ha qualcosa che il tuo sito non ha ancora"

---

## 16. Linguaggio da evitare

**Termini da non usare:**
- *Ranking AI* — non esiste una SERP AI equivalente a Google
- *Posizionarsi su ChatGPT* — ChatGPT non ha posizioni, ha citazioni
- *Il futuro della SEO* — vago, abusato, non azionabile
- *Rivoluzionario* / *innovativo* — claim vuoti
- *Visibilità organica* — connota Google
- *Traffico organico* — connota Google
- *Algoritmo* (usato da solo) — troppo vago, sembra una keyword
- *Ottimizzare per l'AI* senza specificare cosa — ambiguo
- *Garantiamo* (qualsiasi forma) — nessuno può garantire citazioni AI
- *GEO è come la SEO di un tempo* — sminuisce la specificità tecnica del problema

---

## 17. Claim forti ma realistici

Questi claim sono supportati da dati nel codebase o nella ricerca citata:

- "Audit completo in meno di 30 secondi su qualsiasi URL"
- "47 metodi di citability analysis derivati da Princeton KDD 2024"
- "Rileva se i bot AI sono bloccati dal tuo robots.txt prima che sia un problema"
- "Genera llms.txt, ai.txt e schema JSON-LD corretti automaticamente"
- "Confronta il tuo sito con i competitor e identifica esattamente cosa manca"
- "Integrazione CI/CD: blocca il deploy se il punteggio GEO scende sotto soglia"
- "Open source MIT — scoring trasparente, nessun black box"
- "4.000 download/mese, 1.600+ audit eseguiti — dati di maggio 2026"
- "Unico tool che rileva prompt injection nel contenuto del sito"
- "MCP-nativo: usabile direttamente da Claude, Cursor e Windsurf"

---

## 18. Claim da evitare perché troppo esagerati

- ~~"Appari su ChatGPT dopo l'ottimizzazione"~~ — non è controllabile
- ~~"Aumenta le citazioni AI del X%"~~ — non abbiamo dati su questo
- ~~"Il tool più completo per la SEO AI"~~ — "SEO AI" è ambiguo, "più completo" non è verificabile
- ~~"Tutto quello che ti serve per la visibilità AI"~~ — over-promise
- ~~"Sostituisce Semrush per il GEO"~~ — falso: sono strumenti complementari
- ~~"Garantisce visibilità su Perplexity"~~ — nessuno può garantirlo
- ~~"Migliaia di aziende lo usano"~~ — non verificabile al momento
- ~~"Il tool che usano i migliori SEO"~~ — testimonianze non ancora raccolte

---

## 19. Posizionamento consigliato

**Statement di posizionamento principale:**

*GeoReady.dev è lo strumento di audit e monitoring GEO per professionisti che vogliono misurare, correggere e tenere sotto controllo la visibilità AI del proprio sito o dei siti dei propri clienti — senza dipendere da checklist manuali o strumenti SEO che non coprono questo canale.*

**Tre angoli di posizionamento validi (da testare):**

**Angolo 1 — Diagnostico** *(per chi non sa da dove iniziare)*
"Scopri perché il tuo sito non compare nelle risposte AI. Score, breakdown, fix file in 30 secondi."

**Angolo 2 — Professionale/Agenzia** *(per chi deve consegnare valore ai clienti)*
"Il report GEO che puoi consegnare al cliente. Audit in batch, PDF brandizzato, monitoring automatico."

**Angolo 3 — Tecnico/Developer** *(per chi integra nel workflow)*
"Audit GEO in CI/CD. SARIF, JUnit, GitHub Annotations. MCP-native per Claude e Cursor."

**Posizionamento da evitare:**
- Non competere con Semrush/Ahrefs — sono nella stessa categoria per i budget SEO, ma il problema che si risolve è diverso
- Non posizionarsi come "strumento educativo su GEO" — riduce la perceived utility
- Non puntare all'enterprise nella fase attuale — ciclo di vendita lungo, customizzazione richiesta

---

## 20. Opportunità di monetizzazione

**M1 — Monitoring continuo (priorità massima)**
Audit pianificato settimanale/mensile su URL salvati. Notifica su regressione. È il valore che il CLI non può dare senza infrastruttura personale. Giustifica un abbonamento mensile.

**M2 — Batch audit + export (agenzie)**
Upload CSV di URL, audit parallelo, report consolidato. Un'agenzia con 20 clienti non usa il CLI 20 volte. La web app lo fa in un click. Paywall naturale sul volume.

**M3 — Report PDF brandizzabili**
Export PDF con logo agenzia, score visivo, lista fix. Deliverable professionale per clienti. L'endpoint PDF esiste già nel backend. Bassa implementazione, alta perceived value.

**M4 — API access per integratori**
Token API con rate limit per sviluppatori/agenzie che vogliono GEO score nel proprio stack. Pay-per-call o flat mensile.

**M5 — WordPress plugin premium**
Admin widget con GEO score della pagina corrente, fix inline, monitoring attivabile. Distribuzione via WP.org (freemium). Target: consulenti WordPress. Timeline: dopo MVP SaaS.

**M6 — LLM-powered analysis**
Brand sentiment, citation attribution, cross-platform citation map. Già presente come feature opzionale (`[llm]` extra in pyproject.toml). Richiede chiamate API LLM — giustifica piano Pro/Enterprise.

**M7 — White-label reports**
Report con branding personalizzato per agenzie che vogliono presentarlo come servizio proprietario. Piano Agency/Enterprise.

---

## 21. Ipotesi di piani commerciali

### Free (senza registrazione)
- Audit singolo su qualsiasi URL (senza salvataggio)
- Score 0-100 + breakdown 8 categorie
- Raccomandazioni di fix (descrizione, non file generati)
- Badge SVG dinamico
- llms.txt generator base (1 URL)
- Schema validator (JSON-LD input)
- Competitor compare (2 URL, senza storico)
- Report HTML one-time (non scaricabile come PDF)

*Obiettivo: massimizzare il numero di audit eseguiti. L'audit è il funnel, non la barriera.*

---

### Starter — €9/mese · €79/anno
*Target: SEO freelance, founder SaaS, consulente indipendente*
- 5 URL monitorati con audit settimanale automatico
- Alert email su regressione score
- Storico score (90 giorni)
- Export PDF base (branded GeoReady)
- llms.txt generator completo (multi-URL)
- `geo fix` output via web (robots.txt, schema, ai.txt)
- 50 audit API/mese
- 1 confronto competitor/settimana con storico

---

### Pro — €29/mese · €249/anno
*Target: SEO specialist attivo, consulente con 5-15 clienti*
- 20 URL monitorati
- Alert Slack + email con summary settimanale
- Storico illimitato + grafici trend (score nel tempo)
- Batch audit fino a 50 URL (CSV upload)
- PDF brandizzato con logo cliente
- Competitor reports completi con gap analysis
- LLM-powered analysis base (brand sentiment, citation attribution)
- 500 audit API/mese
- Tutti i check avanzati (Trust Stack, RAG Readiness, Prompt Injection, Decay)
- Platform Citation Profile (ChatGPT, Perplexity, Google AI)

---

### Studio — €59/mese · €499/anno
*Target: agenzia piccola (2-5 persone), team SEO interno*
- 50 URL monitorati
- 3 utenti (team access)
- Batch audit fino a 200 URL
- Report condivisibili via link (senza login)
- White-label reports (logo e colori personalizzati)
- Webhook alert su regressione (Slack, Discord, endpoint custom)
- 2.000 audit API/mese
- Priority email support

---

### Agency — €99/mese · €849/anno
*Target: agenzia 5-30 persone con portfolio clienti*
- URL illimitati monitorati
- 10 utenti
- Batch audit illimitato
- Multi-client dashboard (vista aggregata per cliente)
- White-label completo
- API illimitata
- Analisi server log AI crawler (access.log upload)
- Scheduled reports automatici (PDF mensile per cliente)
- Onboarding call dedicata

---

### Enterprise — pricing su misura
*Target: aziende con esigenze custom, team grandi, compliance*
- Tutto di Agency
- SSO (SAML/OIDC)
- SLA definito
- Deployment on-premise disponibile
- Integrazione con strumenti interni (Jira, Linear, Notion via API)
- Account manager dedicato
- Scoring personalizzabile (pesi per settore/mercato)

---

**Note di pricing:**
- Trial 14 giorni senza carta per Starter e Pro
- Upgrade automatico quando si supera il limite URL
- Nessun piano "gratuito con email forzata" — abbassa la perceived value e genera frizione
- Sconto annuale 30% per aumentare LTV

---

## 22. Metriche di successo del prodotto

### Metriche di acquisizione
- **Audit eseguiti/settimana** (total, free + auth)
- **Nuovi utenti registrati/settimana**
- **Conversione audit anonimo → registrazione** (%)
- **Fonte di acquisizione** (GitHub, ricerca organica, referral, social)
- **PyPI downloads/mese** (proxy di salute dell'ecosistema open source)

### Metriche di attivazione
- **% utenti che eseguono almeno 3 audit** nella prima settimana
- **% utenti che salvano almeno 1 URL** per monitoring
- **% utenti che scaricano almeno 1 report PDF**
- **Tempo medio al primo audit** (dalla registrazione)

### Metriche di retention
- **DAU/WAU ratio** (stickiness)
- **URL monitorati per account** (proxy di engagement)
- **% account attivi dopo 30 giorni**
- **Churn mensile** per piano

### Metriche di revenue
- **MRR** (Monthly Recurring Revenue)
- **ARPU** (Average Revenue Per User) per piano
- **LTV/CAC ratio**
- **Upgrade rate** Free → Starter → Pro

### Metriche di prodotto
- **Score medio dei siti auditati** (segnala qualità del targeting)
- **% siti con score < 36** (Critical — alta motivazione al fix)
- **Fix file generati/settimana** (`geo fix` calls)
- **Errori API / timeout** (stabilità)

---

## 23. North Star Metric consigliata

**URL monitorati attivamente dalla base utenti pagante**

**Motivazione:** questa metrica è l'unica che misura contemporaneamente acquisizione (un utente deve registrarsi e pagare), attivazione (deve aver capito il valore), retention (rimane perché riceve valore nel tempo) e intenzione di continuare a pagare (l'URL è il motivo dell'abbonamento).

Un audit one-shot non è un indicatore di salute del business — è un evento. L'URL monitorato è una relazione continuativa.

**Obiettivo a 6 mesi:** 500 URL monitorati da 200+ account paganti.

**Metriche di supporto alla NSM:**
- Audit eseguiti/settimana (alimenta la NSM)
- Alert inviati/settimana (prova che il monitoring funziona e porta valore)
- Fix generati post-alert (prova che l'utente agisce sul valore ricevuto)

---

## 24. Eventi principali da tracciare

Tutti gli eventi usano il prefisso `geo_` per namespace coerente con il sistema di telemetria esistente in `core/telemetry.py`.

### Acquisition
| Evento | Proprietà |
|--------|-----------|
| `geo_page_view` | page, referrer, utm_source, utm_medium |
| `geo_cta_click` | cta_label, page, position |
| `geo_signup_started` | method (email/oauth) |
| `geo_signup_completed` | plan, source |

### Activation
| Evento | Proprietà |
|--------|-----------|
| `geo_audit_run` | url, score, band, duration_ms, format, source (web/api/cli) |
| `geo_audit_completed` | url, score, categories_breakdown, critical_count |
| `geo_fix_generated` | url, fix_types[], source |
| `geo_report_downloaded` | url, format (pdf/html), plan |
| `geo_badge_generated` | url, score, band |

### Engagement
| Evento | Proprietà |
|--------|-----------|
| `geo_url_saved` | url, monitoring_frequency |
| `geo_url_removed` | url, reason |
| `geo_compare_run` | url_count, baseline_url |
| `geo_score_improved` | url, previous_score, new_score, delta |
| `geo_competitor_analysis_run` | url_count |
| `geo_batch_audit_run` | url_count, source (csv/api) |

### Retention & Monetization
| Evento | Proprietà |
|--------|-----------|
| `geo_alert_sent` | url, type (regression/improvement), delta, channel |
| `geo_alert_opened` | alert_id, action_taken |
| `geo_upgrade_prompted` | trigger (url_limit/feature_gate), current_plan |
| `geo_upgrade_completed` | from_plan, to_plan, billing_cycle |
| `geo_subscription_cancelled` | plan, reason, tenure_days |
| `geo_api_key_created` | plan |
| `geo_api_call` | endpoint, url, plan, response_time_ms |

### Negative signals (da monitorare)
| Evento | Motivazione |
|--------|-------------|
| `geo_audit_error` | URL non raggiungibile, timeout, SSRF blocked |
| `geo_session_abandoned` | Utente lascia prima di vedere il risultato |
| `geo_paywall_bounced` | Vede il paywall e non converte — alto segnale di friction |

---

*Documento creato dalla skill `product-marketing-context`. Aggiornare a ogni modifica significativa di prodotto, pricing o posizionamento.*
*Riferimenti tecnici verificati su codebase v4.10.4 — maggio 2026.*
