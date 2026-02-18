# Princeton GEO Methods — I 9 Metodi Ufficiali

> Fonte: "GEO: Generative Engine Optimization" — Aggarwal et al., KDD 2024  
> Paper: https://arxiv.org/abs/2311.09735  
> Dataset/Code: https://generative-engines.com/GEO/  
> Testato su: Perplexity.ai (reale), GPT-4 (simulato), 10,000 query diverse

## Panoramica

La ricerca Princeton ha identificato e testato **9 metodi GEO** su GEO-bench (10,000 query da domini diversi: scienza, storia, legge, finanza, salute...).

**Risultato principale:** I metodi migliori aumentano la visibilità AI fino al **+40%** (con picchi fino a **+115%** per posizioni di ranking specifiche).

La visibilità viene misurata attraverso metriche proprietarie per generative engines:
- **Word Count**: quante parole del tuo contenuto appaiono nella risposta AI
- **Rank Position**: dove viene citata la tua fonte
- **Citation Count**: quante volte sei citato

---

## Metodo 1 — Cite Sources (Citazione Fonti)

**Impatto stimato: +30–115% per visibilità AI**

### Descrizione
Aggiungere link e riferimenti a fonti autorevoli esterne direttamente nel testo della pagina. Questo è il metodo con l'impatto **più variabile** ma potenzialmente più alto: +115% per rank-5 position.

### Come implementarlo
1. Identifica ogni claim/affermazione nel tuo contenuto
2. Cerca e linka la fonte primaria (paper, studio, sito ufficiale)
3. Usa formato: `Secondo [Fonte](URL), ...`
4. Linka preferibilmente: paper accademici, siti governativi (.gov, .edu), report di settore

### Esempio pratico
**Prima:** "Il mutuo a tasso fisso è più sicuro in periodi di inflazione."  
**Dopo:** "Secondo la [Banca d'Italia](https://bancaditalia.it), il mutuo a tasso fisso protegge meglio il debitore in periodi inflazionistici superiori al 3%."

### Note
- Particolarmente efficace per query informative e transazionali
- Gli AI engines usano la presenza di citazioni come segnale di affidabilità
- Effetto variabile: può essere negativo per rank-1 ma molto positivo per rank-3+

---

## Metodo 2 — Statistics (Statistiche e Dati)

**Impatto stimato: +40% visibilità media**

### Descrizione
Includere dati quantitativi specifici, percentuali, numeri concreti e metriche misurabili nel contenuto. Gli AI engines tendono a preferire contenuti con fatti verificabili.

### Come implementarlo
1. Sostituisci affermazioni generiche con dati numerici specifici
2. Includi: percentuali, valori monetari, date, dimensioni, risultati di studi
3. Specifica sempre la fonte e l'anno del dato
4. Usa contesti numerici comparativi ("rispetto al 2023, +15%")

### Esempio pratico
**Prima:** "Molti italiani investono in fondi comuni."  
**Dopo:** "Il 34,2% degli italiani possiede quote di fondi comuni di investimento (Consob, 2024), con un patrimonio totale di €1.200 miliardi gestiti da SGR."

### Note
- Funziona meglio combinato con Cite Sources
- I numeri specifici aumentano la probabilità di essere estratti e citati
- Evita statistiche troppo vecchie (>3 anni) o imprecise

---

## Metodo 3 — Quotation Addition (Citazioni Dirette)

**Impatto stimato: +30–40% visibilità**

### Descrizione
Includere citazioni testuali tra virgolette di esperti, autorità o documenti ufficiali. Le virgolette segnalano agli AI che il contenuto è attribuito e verificabile.

### Come implementarlo
1. Cerca citazioni di esperti rilevanti (CEO, ricercatori, regolatori)
2. Usa il formato: `"Testo citazione" — Nome Esperto, Ruolo, Anno`
3. Includi almeno 1-2 citazioni per pagina
4. Cita anche documenti ufficiali: leggi, normative, standard

### Esempio pratico
```
"Il tasso fisso è la scelta giusta quando i tassi di mercato 
sono sotto la media storica" — Mario Rossi, Responsabile 
Mutui Mediobanca, Sole24Ore 2024
```

### Note
- Molto efficace per domini Finanza, Salute, Legale (YMYL)
- Gli AI preferiscono contenuti con attribuzione chiara
- Alternare citazioni brevi e spiegate nel contesto

---

## Metodo 4 — Authoritative (Tono Autorevole)

**Impatto stimato: +6–12% visibilità media**

### Descrizione
Riscrivere il contenuto con un tono da esperto settoriale invece di un tono generico. Include: uso di terminologia precisa, struttura logica, assenza di vaguezza.

### Come implementarlo
1. Elimina frasi vaghe: "spesso", "in genere", "potrebbe"
2. Usa terminologia tecnica corretta del settore
3. Struttura con: definizione → spiegazione → implicazioni pratiche
4. Aggiungi contesto professionale: "Dal punto di vista finanziario..."
5. Evita tono commerciale/promozionale

### Esempio pratico
**Prima:** "Il mutuo potrebbe fare al caso vostro se avete bisogno di comprare casa."  
**Dopo:** "Il mutuo ipotecario è uno strumento di finanziamento a lungo termine (15-30 anni) garantito da ipoteca sull'immobile. La rata comprende quota capitale e interessi calcolati sul tasso concordato (fisso o variabile)."

### Note
- Impatto più costante rispetto agli altri metodi
- Particolarmente importante per domini YMYL (finance, health, legal)
- Combinare con Technical Terms per risultati migliori

---

## Metodo 5 — Fluency Optimization (Ottimizzazione Fluency)

**Impatto stimato: +15–30% visibilità**

### Descrizione
Migliorare la fluidità e leggibilità del testo. Testo scorrevole, ben strutturato e coerente viene preferito dai modelli LLM per l'estrazione di informazioni.

### Come implementarlo
1. Usa frasi di lunghezza media (15-25 parole)
2. Varia la struttura delle frasi
3. Elimina errori grammaticali e refusi
4. Usa connettivi logici: "quindi", "tuttavia", "di conseguenza", "in particolare"
5. Struttura paragrafi con: topic sentence → sviluppo → conclusione

### Tools utili
- Grammarly / LanguageTool per errori
- Hemingway App per leggibilità
- Testare con reading level score

### Esempio pratico
**Prima:** "Il calcolo del mutuo, che è fatto dalla banca, dipende dal tasso. Il tasso può essere fisso o variabile. Bisogna scegliere."  
**Dopo:** "Il calcolo della rata mutuo dipende principalmente dal tipo di tasso scelto. Un tasso fisso garantisce rate stabili per tutta la durata del finanziamento, mentre un tasso variabile può ridursi o aumentare in base all'Euribor."

---

## Metodo 6 — Easy-to-Understand (Semplificazione)

**Impatto stimato: +8–15% visibilità**

### Descrizione
Semplificare il linguaggio tecnico complesso senza perdere precisione. Gli AI preferiscono testo comprensibile che può essere estratto e parafrasato facilmente.

### Come implementarlo
1. Dopo ogni termine tecnico, aggiungi una spiegazione breve tra parentesi
2. Usa analogie per concetti complessi
3. Crea glossari per termini di settore
4. Struttura con "Cos'è", "Come funziona", "Quando usarlo"

### Esempio pratico
**Prima:** "Il loan-to-value ratio influenza l'LTV delle garanzie accessorie."  
**Dopo:** "Il rapporto prestito/valore (LTV, Loan-To-Value) misura quanto del prezzo casa stai chiedendo in prestito. Un LTV del 80% significa che finanzi l'80% del valore, il restante 20% è il tuo anticipo."

### Note
- Non sacrificare la precisione per la semplicità
- Usa struttura a due livelli: spiegazione semplice + dettagli tecnici

---

## Metodo 7 — Unique Words (Vocabolario Ricco)

**Impatto stimato: +5–8% visibilità**

### Descrizione
Arricchire il vocabolario evitando ripetizioni eccessive. Un vocabolario vario segnala qualità del contenuto.

### Come implementarlo
1. Identifica le parole ripetute con strumenti come WordCounter
2. Usa sinonimi contestualmente appropriati
3. Alterna tra termini tecnici e termini comuni per lo stesso concetto
4. Usa un thesaurus di settore

### Nota
Impatto **minore** rispetto agli altri metodi. Non prioritizzare.

---

## Metodo 8 — Technical Terms (Terminologia Tecnica)

**Impatto stimato: +5–10% per query specializzate**

### Descrizione
Usare terminologia tecnica specifica del settore in modo appropriato. Aumenta la rilevanza per query specializzate da utenti esperti.

### Come implementarlo
1. Includi acronimi ufficiali (TAN, TAEG, LTV, ROI)
2. Usa termini standard del settore nella loro forma corretta
3. Non esagerare: bilanciare technical terms con Easy-to-Understand

### Esempio
"TAEG (Tasso Annuo Effettivo Globale)", "Euribor 3M", "spread creditizio", "ammortamento alla francese"

### Nota
Funziona in **combinazione** con Authoritative e Cite Sources.

---

## Metodo 9 — Keyword Stuffing ⚠️

**Impatto stimato: Neutro o NEGATIVO**

### Descrizione
Inserire forzatamente parole chiave nel testo con alta densità. La ricerca Princeton ha dimostrato che **non è efficace** per GEO e può essere controproducente.

### Risultato ricerca
- Nessun miglioramento significativo nella visibilità AI
- Può peggiorare Fluency (−impatto netto)
- Tecnica residua da SEO tradizionale, **non applicare per GEO**

### Cosa fare invece
Usa Fluency Optimization + Cite Sources + Statistics per risultati reali.

---

## Riepilogo Impatto per Dominio

| Metodo | Scienze | Finanza | Salute | Storia | Media |
|--------|---------|---------|--------|--------|-------|
| Cite Sources | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| Statistics | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| Quotation | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐ |
| Authoritative | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐ |
| Fluency | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| Easy-Understand | ⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐ | ⭐⭐⭐ |

---

## Strategia Implementazione Consigliata

### Fase 1 — Quickwins (settimana 1-2)
1. **Statistics**: aggiungi dati numerici alle pagine principali (+40%)
2. **Cite Sources**: aggiungi 2-3 link a fonti autorevoli per pagina (+30%)
3. **Fluency**: revisiona testo per scorrevolezza

### Fase 2 — Ottimizzazione (settimana 3-4)
4. **Quotation Addition**: aggiungi citazioni di esperti
5. **Authoritative**: riorganizza contenuto con struttura da esperto
6. **Technical Terms**: verifica terminologia corretta

### Fase 3 — Fine Tuning
7. **Easy-to-Understand**: aggiungi glossari e spiegazioni
8. **Unique Words**: revisiona ripetizioni

> ⚠️ **Non fare**: Keyword Stuffing (metodo 9) — controproducente per GEO

---

## Riferimenti

- Paper originale: https://arxiv.org/abs/2311.09735
- Princeton Collaborate: https://collaborate.princeton.edu/en/publications/geo-generative-engine-optimization/
- GEO-bench dataset: https://generative-engines.com/GEO/
- KDD 2024 Conference: August 25-29, 2024, Barcelona
