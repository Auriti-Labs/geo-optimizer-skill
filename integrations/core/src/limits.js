// Limiti sull'input, allineati al motore Python. Le dimensioni sono in byte UTF-8, non in unità UTF-16.

/** Tetto di robots.txt (RFC 9309 §2.5), come `_MAX_ROBOTS_BYTES` in geo_optimizer.utils.robots_parser. */
export const MAX_ROBOTS_BYTES = 500 * 1024;

/** Tetto predefinito dell'HTML di una pagina, come `MAX_RESPONSE_SIZE` in geo_optimizer.models.config. */
export const DEFAULT_MAX_HTML_BYTES = 10 * 1024 * 1024;

/** `text` pesa più di `limit` byte UTF-8? Codifica solo se la lunghezza non basta a decidere (1-3 byte per unità). */
export function exceedsUtf8Bytes(text, limit) {
  if (text.length > limit) return true;
  if (text.length * 3 <= limit) return false;
  return new TextEncoder().encode(text).length > limit;
}
