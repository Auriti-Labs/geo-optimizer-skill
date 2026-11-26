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
  if (d !== undefined && (d < 1 || d > new Date(Date.UTC(y, mo, 0)).getUTCDate())) return false;
  const time = value.match(/T(\d{2}):(\d{2})(?::(\d{2}))?/);
  if (time && (Number(time[1]) > 23 || Number(time[2]) > 59 || Number(time[3] ?? 0) > 59)) return false;
  return true;
}
