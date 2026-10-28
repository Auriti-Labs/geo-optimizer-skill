# GEO Optimizer Web — Local Development

## Architecture

- **Frontend**: Astro 5 + React islands + Tailwind CSS 4 (porta 4321)
- **Backend**: FastAPI esistente (porta 8000)
- **Proxy**: Vite proxy in astro.config.mjs inoltra `/api` e `/badge` al backend

## Prerequisiti

- Node.js 20+ (via volta/nvm)
- Python 3.10+ con geo-optimizer-skill installato

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

## Produzione e API base

Il proxy Vite in `astro.config.mjs` funziona **solo in sviluppo** (`npm run dev`).

In produzione (build statico) il frontend non ha un server proxy. Servono due opzioni:

1. **Reverse proxy** (Nginx, Cloudflare, Vercel rewrite) che inoltra `/api/*` al backend sotto lo stesso dominio.
2. **Variabile d'ambiente `PUBLIC_API_BASE`** — esporta un URL assoluto prima della build:
   ```bash
   PUBLIC_API_BASE=https://api.geoready.dev npm run build
   ```
   `src/lib/api.ts` legge `import.meta.env.PUBLIC_API_BASE` e lo usa come prefisso per le chiamate API.

Il frontend statico **non deve assumere** che `/api` sia disponibile sullo stesso dominio senza una di queste due configurazioni.

**Nota su `PUBLIC_API_BASE`**: la variabile deve contenere il **prefisso API completo**.
- Con reverse proxy sotto lo stesso dominio: `PUBLIC_API_BASE=/api`
- Con backend su dominio esterno: `PUBLIC_API_BASE=https://api.geoready.dev` (se l'API e servita da root) oppure `PUBLIC_API_BASE=https://api.geoready.dev/api` (se il backend monta le route sotto `/api`).

## Mock data (senza backend)

Se il backend non e attivo, la pagina report mostrera un errore di rete dopo la navigazione.
Per testare l'UI senza backend, usa `/report/demo` che carica dati mock statici.

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
- I font (Geist, Geist Mono) sono self-hosted in `public/fonts/`, gli stessi file di app.geoready.dev — nessuna richiesta a Google Fonts.
- Il cookie banner GDPR va implementato in una fase successiva come componente React.
