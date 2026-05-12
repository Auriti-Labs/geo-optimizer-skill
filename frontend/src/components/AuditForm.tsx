import { useState } from 'react';

export default function AuditForm() {
  const [url, setUrl] = useState('');
  const [status, setStatus] = useState<'idle' | 'loading' | 'error' | 'success'>('idle');
  const [result, setResult] = useState<any>(null);
  const [errorMsg, setErrorMsg] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;

    setStatus('loading');
    setErrorMsg('');
    setResult(null);

    try {
      const res = await fetch(`/api/audit?url=${encodeURIComponent(url)}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Audit failed');
      setResult(data);
      setStatus('success');
    } catch (err: any) {
      setErrorMsg(err.message || 'Unknown error');
      setStatus('error');
    }
  };

  return (
    <div className="space-y-6">
      <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3">
        <input
          type="url"
          required
          placeholder="https://example.com"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          className="flex-1 px-4 py-3 rounded-lg border border-border bg-bg-surface text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-accent-teal focus:border-transparent transition-shadow"
        />
        <button
          type="submit"
          disabled={status === 'loading'}
          className="px-6 py-3 rounded-lg bg-accent-teal text-white font-medium text-sm hover:bg-accent-teal-dark disabled:opacity-50 disabled:cursor-not-allowed transition-colors shrink-0"
        >
          {status === 'loading' ? 'Analyzing...' : 'Run Audit'}
        </button>
      </form>

      {status === 'error' && (
        <div className="p-4 rounded-lg border border-accent-danger/20 bg-accent-danger/5 text-accent-danger text-sm">
          {errorMsg}
        </div>
      )}

      {status === 'success' && result && (
        <div className="p-6 rounded-xl border border-border bg-bg-surface space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-display text-lg font-semibold">Audit Result</h3>
            <span className="font-mono text-2xl font-bold text-accent-teal">
              {result.geo_score ?? result.score ?? 'N/A'}/100
            </span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {Object.entries(result.category_scores ?? {}).map(([key, val]: [string, any]) => (
              <div key={key} className="p-3 rounded-lg border border-border bg-bg-base">
                <div className="text-[10px] uppercase tracking-wider text-text-muted font-mono">{key}</div>
                <div className="font-mono text-sm font-semibold mt-1">{val?.score ?? val ?? 0}</div>
              </div>
            ))}
          </div>
          {result.recommendations && (
            <div className="pt-4 border-t border-border">
              <h4 className="text-sm font-semibold mb-2">Recommendations ({result.recommendations.length})</h4>
              <ul className="space-y-1.5">
                {result.recommendations.slice(0, 5).map((rec: any, i: number) => (
                  <li key={i} className="text-sm text-text-secondary flex items-start gap-2">
                    <span className="w-1 h-1 rounded-full bg-accent-teal mt-2 shrink-0" />
                    {rec.message || rec}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
