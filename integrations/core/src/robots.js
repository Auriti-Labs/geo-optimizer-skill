// robots.txt secondo RFC 9309: gruppi per User-agent, longest match, Allow vince a parità.
// Specchio di geo_optimizer.utils.robots_parser (con wildcards=True). Zero dipendenze.

const MAX_BYTES = 500 * 1024;

/** @returns {Map<string, {allow: string[], disallow: string[]}>} regole per agente (minuscolo). */
export function parseRobots(content) {
  let text = String(content ?? '');
  if (text.charCodeAt(0) === 0xfeff) text = text.slice(1);
  if (text.length > MAX_BYTES) text = text.slice(0, MAX_BYTES);

  const groups = new Map();
  let agents = [];
  let lastWasAgent = false;
  for (const raw of text.split(/\r\n|\n|\r/)) {
    const line = raw.split('#')[0].trim();
    if (!line) continue;
    const colon = line.indexOf(':');
    if (colon < 0) continue;
    const key = line.slice(0, colon).trim().toLowerCase();
    const value = line.slice(colon + 1).trim();
    if (key === 'user-agent') {
      if (!lastWasAgent) agents = [];
      const name = value.toLowerCase();
      agents.push(name);
      if (!groups.has(name)) groups.set(name, { allow: [], disallow: [] });
      lastWasAgent = true;
      continue;
    }
    // Sitemap, Host e chiavi sconosciute non sono membri di un gruppo: non interrompono i User-agent impilati.
    if (key === 'crawl-delay') lastWasAgent = false;
    if (key !== 'allow' && key !== 'disallow') continue;
    lastWasAgent = false;
    for (const name of agents) groups.get(name)[key].push(value);
  }
  return groups;
}

const UNRESERVED = /^[A-Za-z0-9\-._~]$/;

// Una sola grafia per regola e percorso (RFC 9309 §2.2.2): i caratteri non ASCII diventano escape UTF-8,
// l'esadecimale è maiuscolo, gli escape di caratteri non riservati sono decodificati. `%2F` resta codificato.
function normalizePath(value) {
  const encoded = Array.from(value, (ch) => (/^[A-Za-z0-9/%:@!$&'()*+,;=?\-._~]$/.test(ch) ? ch : encodeURIComponent(ch))).join('');
  return encoded.replace(/%([0-9A-Fa-f]{2})/g, (match, hex) => {
    const ch = String.fromCharCode(parseInt(hex, 16));
    return UNRESERVED.test(ch) ? ch : `%${hex.toUpperCase()}`;
  });
}

// Confronta i pezzi di una regola tra i `*` con il percorso, senza espressioni regolari: una regex costruita
// dalla stessa regola va in backtracking senza limite su un robots.txt ostile come `/a*a*a*a*a*b`.
function globMatches(parts, path, anchored) {
  const [first, ...rest] = parts;
  if (!path.startsWith(first)) return false;
  let pos = first.length;
  if (rest.length === 0) return anchored ? pos === path.length : true;
  const last = rest[rest.length - 1];
  for (const piece of rest.slice(0, -1)) {
    const found = path.indexOf(piece, pos);
    if (found < 0) return false;
    pos = found + piece.length;
  }
  if (anchored) return path.length - last.length >= pos && path.endsWith(last);
  return path.indexOf(last, pos) >= 0;
}

function ruleMatches(rule, path) {
  // `*` = qualsiasi sequenza, `$` finale = ancora di fine; il resto è un prefisso letterale.
  const anchored = rule.endsWith('$');
  const body = anchored ? rule.slice(0, -1) : rule;
  return globMatches(normalizePath(body).split('*'), normalizePath(path), anchored);
}

/** true = consentito, false = bloccato, null = nessuna regola applicabile. */
function decide(rules, path) {
  let bestLength = -1;
  let decision = null;
  for (const rule of rules.disallow) {
    if (!rule || !ruleMatches(rule, path)) continue;
    if (rule.length > bestLength) {
      bestLength = rule.length;
      decision = false;
    }
  }
  for (const rule of rules.allow) {
    if (!rule || !ruleMatches(rule, path)) continue;
    if (rule.length >= bestLength) {
      bestLength = rule.length;
      decision = true;
    }
  }
  return decision;
}

/** Il bot è bloccato su `path`? Gruppo del bot, altrimenti `*`; nessun gruppo = consentito. */
export function isBlocked(robotsTxt, bot, path) {
  const groups = parseRobots(robotsTxt);
  const rules = groups.get(String(bot).toLowerCase()) ?? groups.get('*');
  if (!rules) return false;
  return decide(rules, path || '/') === false;
}
