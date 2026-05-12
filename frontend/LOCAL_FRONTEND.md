# GEO Optimizer Web — Local Development

## Architecture

- **Frontend**: Astro 5 + React islands + Tailwind CSS 4 (porta 4321)
- **Backend**: FastAPI esistente (porta 8000)
- **Proxy**: Vite proxy in astro.config.mjs inoltra `/api`, `/report`, `/badge` al backend

## Prerequisiti

- Node.js 20+ (via volta/nvm)
- Python 3.9+ con geo-optimizer-skill installato

## Avvio locale

### 1. Backend FastAPI

```bash
cd /home/camilo/geo-optimizer-skill
source .venv/bin/activate  # se usi venv
geo-web --port 8000
```

Il backend espone le API su `http://localhost:8000`.

### 2. Frontend Astro

In un altro terminale:

```bash
cd /home/camilo/geo-optimizer-skill/frontend
npm run dev
```

Il frontend gira su `http://localhost:4321`.

Il proxy Vite in `astro.config.mjs` inoltra automaticamente le chiamate `/api/*` al backend su porta 8000.

### 3. Verifica

Apri il browser su `http://localhost:4321`.

Prova a eseguire un audit: il form chiamera `/api/audit?url=...` che viene proxato al backend.

## Mock data (senza backend)

Se il backend non e attivo, il form audit mostrera un errore di rete.
Per testare l'UI senza backend, modifica `src/components/AuditForm.tsx` per usare mock data.

## Build produzione

```bash
npm run build
```

Output in `dist/` — puro HTML statico con React islands hydratate.

## Struttura progetto

```
frontend/
├── astro.config.mjs          # Config Astro + Vite proxy
├── src/
│   ├── layouts/Layout.astro    # Layout base con meta tag
│   ├── components/
│   │   ├── Shell.astro       # Wrapper nav + footer
│   │   ├── Navbar.astro        # Nav responsive
│   │   ├── Footer.astro        # Footer dark
│   │   └── AuditForm.tsx      # Form interattivo React
│   ├── pages/
│   │   ├── index.astro       # Home
│   │   ├── compare.astro     # Confronto
│   │   ├── analyze-competitors.astro
│   │   ├── manifesto.astro
│   │   ├── roadmap.astro
│   │   ├── research.astro
│   │   └── privacy.astro
│   └── styles/global.css     # Design tokens + Tailwind
└── public/                    # Asset statici
```

## Note

- Nessuna modifica al backend Python — il frontend e completamente separato.
- I font sono self-hosted via `@fontsource` — nessuna richiesta a Google Fonts.
- Il cookie banner GDPR va implementato in una fase successiva come componente React.
