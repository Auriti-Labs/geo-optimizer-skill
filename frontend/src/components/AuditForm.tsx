import { useState } from 'react';

/** Verifica se una stringa sembra un URL valido. */
function isValidUrl(value: string): boolean {
  if (!value.trim()) return false;
  try {
    const parsed = new URL(value);
    return parsed.protocol === 'http:' || parsed.protocol === 'https:';
  } catch {
    return false;
  }
}

export default function AuditForm() {
  const [url, setUrl] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg('');

    const trimmed = url.trim();
    if (!trimmed) {
      setErrorMsg('Inserisci un URL da analizzare.');
      return;
    }

    if (!isValidUrl(trimmed)) {
      setErrorMsg('Inserisci un URL valido (es. https://example.com).');
      return;
    }

    // Naviga verso la pagina report che esegue l'audit reale
    window.location.href = `/report/audit?url=${encodeURIComponent(trimmed)}`;
  };

  return (
    <div className="space-y-4">
      <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3">
        <input
          type="url"
          required
          placeholder="https://example.com"
          value={url}
          onChange={(e) => {
            setUrl(e.target.value);
            if (errorMsg) setErrorMsg('');
          }}
          className="flex-1 px-4 py-3 rounded-lg border border-border bg-bg-surface text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-accent-teal focus:border-transparent transition-shadow"
        />
        <button
          type="submit"
          className="px-6 py-3 rounded-lg bg-accent-teal text-white font-medium text-sm hover:bg-accent-teal-dark transition-colors shrink-0"
        >
          Run Audit
        </button>
      </form>

      {errorMsg && (
        <div className="p-4 rounded-lg border border-accent-danger/20 bg-accent-danger/5 text-accent-danger text-sm">
          {errorMsg}
        </div>
      )}
    </div>
  );
}
