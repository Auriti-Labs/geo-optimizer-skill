import { useState } from 'react';
import { trackPricingObjection } from '../lib/geo_track';

/**
 * PricingObjectionSurvey — micro-survey a 1 domanda in fondo a /pricing/.
 *
 * Nessun backend: ogni click invia solo l'evento GA4 `geo_pricing_objection`
 * via geo_track.ts (silenzioso senza consenso analytics) e mostra un
 * ringraziamento inline. Il campo libero è opzionale e troncato a 200 caratteri.
 */

const REASONS = [
  { value: 'unclear_pro_value', label: "I don't understand what Pro adds" },
  { value: 'price', label: 'Price' },
  { value: 'need_to_see_product', label: 'I need to see the product first' },
  { value: 'just_researching', label: 'Just researching' },
] as const;

const MAX_NOTE_LENGTH = 200;

export default function PricingObjectionSurvey() {
  const [selected, setSelected] = useState<string | null>(null);
  const [note, setNote] = useState('');
  const [submitted, setSubmitted] = useState(false);

  function handleReasonClick(reason: string) {
    setSelected(reason);
    // L'evento parte al click sull'opzione: la nota libera è un follow-up separato.
    trackPricingObjection({ reason });
  }

  function handleNoteSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!selected) return;
    const trimmed = note.trim().slice(0, MAX_NOTE_LENGTH);
    if (trimmed) {
      trackPricingObjection({ reason: selected, note: trimmed });
    }
    setSubmitted(true);
  }

  if (submitted) {
    return (
      <div className="p-6 rounded-[--radius-lg] border border-border bg-bg-surface text-center">
        <p className="text-sm font-semibold text-text-primary">Thanks — that helps.</p>
        <p className="mt-1 text-sm text-text-secondary">
          Your answer directly shapes what we improve on this page.
        </p>
      </div>
    );
  }

  return (
    <div className="p-6 md:p-8 rounded-[--radius-lg] border border-border bg-bg-surface">
      <p className="text-[10px] font-mono text-text-muted uppercase tracking-wider mb-2">
        One quick question
      </p>
      <p className="text-base font-semibold text-text-primary">
        Not ready yet? What's stopping you today?
      </p>

      <div className="mt-4 flex flex-wrap gap-2">
        {REASONS.map((r) => (
          <button
            key={r.value}
            type="button"
            onClick={() => handleReasonClick(r.value)}
            aria-pressed={selected === r.value}
            className={`px-4 py-2 rounded-full border text-sm transition-colors ${
              selected === r.value
                ? 'border-accent-teal bg-accent-teal/10 text-accent-teal font-semibold'
                : 'border-border text-text-secondary hover:border-accent-teal/50 hover:text-text-primary'
            }`}
          >
            {r.label}
          </button>
        ))}
      </div>

      {selected && (
        <form onSubmit={handleNoteSubmit} className="mt-4 flex flex-col sm:flex-row gap-2">
          <input
            type="text"
            value={note}
            maxLength={MAX_NOTE_LENGTH}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Anything else? (optional)"
            className="flex-1 px-3 py-2 rounded-[--radius-md] border border-border bg-bg-surface text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-teal focus:ring-1 focus:ring-accent-teal/30"
          />
          <button
            type="submit"
            className="shrink-0 px-4 py-2 rounded-[--radius-md] border border-border text-sm font-semibold text-text-primary hover:bg-bg-subtle transition-colors"
          >
            Send
          </button>
        </form>
      )}

      <p className="mt-3 text-[10px] text-text-muted">
        Anonymous — used only to improve this page. No email required.
      </p>
    </div>
  );
}
