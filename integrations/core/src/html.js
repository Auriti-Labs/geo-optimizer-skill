// Estrazione minima dall'HTML senza parser: solo ciò che servono le cinque regole.
// Limite dichiarato: regex su HTML ben formato; un parser vero resta nel motore Python.

const ATTR = /([^\s"'<>/=]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+)))?/g;

function attributes(tag) {
  const out = {};
  const inner = tag.replace(/^<\s*[a-zA-Z0-9]+/, '').replace(/\/?>$/, '');
  for (const m of inner.matchAll(ATTR)) {
    out[m[1].toLowerCase()] = m[2] ?? m[3] ?? m[4] ?? '';
  }
  return out;
}

// Un tag può contenere `>` dentro un attributo tra virgolette.
const TAG = (name) => new RegExp(`<${name}\\b(?:[^>"']|"[^"]*"|'[^']*')*>`, 'gi');

const withoutComments = (html) => html.replace(/<!--[\s\S]*?-->/g, '');

// Il <head> si cerca senza commenti e senza il corpo degli script, che possono contenere `</head>` o un <link>.
function headOf(html) {
  const clean = withoutComments(html).replace(/<script\b[^>]*>[\s\S]*?<\/script\s*>/gi, '');
  const close = clean.search(/<\/head\s*>/i);
  return close >= 0 ? clean.slice(0, close) : clean;
}

/** URL di ogni <link rel="canonical"> nel <head> (Google ignora quelli fuori). */
export function canonicals(html) {
  const out = [];
  for (const m of headOf(String(html)).matchAll(TAG('link'))) {
    const a = attributes(m[0]);
    const rel = (a.rel || '').toLowerCase().split(/\s+/);
    if (rel.includes('canonical') && a.href !== undefined) out.push(a.href.trim());
  }
  return out;
}

/** Direttive di <meta name="robots|googlebot|bingbot">, minuscole e senza spazi. */
export function robotsDirectives(html) {
  const out = new Set();
  for (const m of withoutComments(String(html)).matchAll(TAG('meta'))) {
    const a = attributes(m[0]);
    if (!['robots', 'googlebot', 'bingbot'].includes((a.name || '').toLowerCase())) continue;
    for (const d of (a.content || '').split(',')) {
      const v = d.trim().toLowerCase().replace(/\s+/g, '');
      if (v) out.add(v);
    }
  }
  // `none` equivale a `noindex, nofollow`.
  if (out.has('none')) {
    out.add('noindex');
    out.add('nofollow');
  }
  return out;
}

/** Corpo testuale di ogni <script type="application/ld+json">. */
export function jsonLdBlocks(html) {
  const out = [];
  for (const m of withoutComments(String(html)).matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script\s*>/gi)) {
    const a = attributes(`<script ${m[1]}>`);
    if ((a.type || '').toLowerCase().split(';')[0].trim() === 'application/ld+json') out.push(m[2]);
  }
  return out;
}
