/**
 * URL normalisation and validation for user-typed input.
 *
 * Every audit form on the site asks for a website, and every placeholder shows a
 * bare hostname ("example.com"). The inputs used to be `type="url"`, which made
 * the browser reject exactly that during native constraint validation — before
 * any submit handler could prepend a scheme. Users had to type "https://" by hand
 * to get past a field whose own placeholder told them not to.
 *
 * The inputs are now `type="text"` with `inputMode="url"` (URL keyboard on mobile,
 * no scheme requirement), which moves the whole job here. `normalizeUrl` supplies
 * the scheme; `isValidUrl` has to carry the weight `type="url"` used to, because
 * prepending "https://" makes `new URL()` accept strings a user never meant as a
 * site: "a" parses with hostname "a", "..." with hostname "...", and "ftp://x.com"
 * becomes "https://ftp://x.com" with hostname "ftp".
 *
 * The backend normalises independently (`validators.resolve_and_validate_url`), so
 * this is about giving a readable message instead of a server error — never the
 * only line of defence.
 */

/** Prepend `https://` unless the value already carries an http(s) scheme. */
export function normalizeUrl(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) return '';
  if (!/^https?:\/\//i.test(trimmed)) {
    return `https://${trimmed}`;
  }
  return trimmed;
}

/**
 * True when `value` parses as an http(s) URL with a plausible public hostname.
 *
 * Pass an already-normalised value. The hostname pattern requires at least one
 * dot-separated label plus a two-letter-or-longer TLD, which accepts subdomains,
 * multi-part TLDs (`site.co.uk`), punycode (`xn--80ak6aa92e.com`) and explicit
 * ports, while rejecting bare words and single labels like `localhost`.
 */
export function isValidUrl(value: string): boolean {
  if (!value.trim()) return false;

  let parsed: URL;
  try {
    parsed = new URL(value);
  } catch {
    return false;
  }

  if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') return false;

  return /^[a-z0-9-]+(\.[a-z0-9-]+)*\.[a-z]{2,}$/i.test(parsed.hostname);
}

/** Normalise then validate. Returns the normalised URL, or null if unusable. */
export function toAuditableUrl(value: string): string | null {
  const normalized = normalizeUrl(value);
  return isValidUrl(normalized) ? normalized : null;
}
