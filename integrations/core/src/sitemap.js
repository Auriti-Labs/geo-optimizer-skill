// Lettura di una sitemap XML: <loc> e <lastmod> di ogni <url>. Un sitemapindex è riconosciuto, non seguito.

function decode(value) {
  return value
    .replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, '$1')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&apos;/g, "'")
    .replace(/&amp;/g, '&')
    .trim();
}

function tag(block, name) {
  const m = block.match(new RegExp(`<(?:[\\w-]+:)?${name}\\b[^>]*>([\\s\\S]*?)</(?:[\\w-]+:)?${name}\\s*>`, 'i'));
  return m ? decode(m[1]) : undefined;
}

/** @returns {{index: boolean, entries: {loc: string, lastmod?: string}[]}} */
export function parseSitemap(xml) {
  const text = String(xml ?? '');
  if (/<(?:[\w-]+:)?sitemapindex\b/i.test(text)) {
    const entries = [...text.matchAll(/<(?:[\w-]+:)?sitemap\b[^>]*>([\s\S]*?)<\/(?:[\w-]+:)?sitemap\s*>/gi)]
      .map((m) => ({ loc: tag(m[1], 'loc'), lastmod: tag(m[1], 'lastmod') }))
      .filter((e) => e.loc);
    return { index: true, entries };
  }
  const entries = [...text.matchAll(/<(?:[\w-]+:)?url\b[^>]*>([\s\S]*?)<\/(?:[\w-]+:)?url\s*>/gi)]
    .map((m) => ({ loc: tag(m[1], 'loc'), lastmod: tag(m[1], 'lastmod') }))
    .filter((e) => e.loc);
  return { index: false, entries };
}

// W3C Datetime: YYYY, YYYY-MM, YYYY-MM-DD o con ora e fuso (sitemaps.org).
const W3C = /^\d{4}(-\d{2}(-\d{2}(T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:\d{2}))?)?)?$/;

export function isValidLastmod(value) {
  if (typeof value !== 'string' || !W3C.test(value)) return false;
  const [y, mo, d] = value.slice(0, 10).split('-').map(Number);
  if (mo !== undefined && (mo < 1 || mo > 12)) return false;
  if (d !== undefined && (d < 1 || d > daysInMonth(y, mo))) return false;
  const time = value.match(/T(\d{2}):(\d{2})(?::(\d{2}))?/);
  if (time && (Number(time[1]) > 23 || Number(time[2]) > 59 || Number(time[3] ?? 0) > 59)) return false;
  // Il fuso `+hh:mm` deve essere un orario reale: `+99:99` e `+01:60` non lo sono.
  const zone = value.match(/[+-](\d{2}):(\d{2})$/);
  if (zone && (Number(zone[1]) > 23 || Number(zone[2]) > 59)) return false;
  return true;
}

// Date.UTC mappa gli anni 0-99 al 1900: il calendario si calcola a mano.
function daysInMonth(year, month) {
  if (month === 2) return (year % 4 === 0 && year % 100 !== 0) || year % 400 === 0 ? 29 : 28;
  return [4, 6, 9, 11].includes(month) ? 30 : 31;
}
