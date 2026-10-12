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
      <div className="rounded-[4px] border border-rail bg-white p-6 text-center">
        <p className="text-sm font-semibold text-ink">Thanks, that helps.</p>
        <p className="mt-1 text-sm text-ink-soft">
          Your answer directly shapes what we improve on this page.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-[4px] border border-rail bg-white p-6 md:p-8">
      <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
        <p className="text-base font-semibold text-ink">
          Not ready yet? What's stopping you today?
        </p>
        <p className="font-mono text-[11px] uppercase tracking-[0.12em] text-ink-mute">
          One quick question
        </p>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {REASONS.map((r) => (
          <button
            key={r.value}
            type="button"
            onClick={() => handleReasonClick(r.value)}
            aria-pressed={selected === r.value}
            className={`rounded-[2px] border px-4 py-2 text-sm transition-colors ${
              selected === r.value
                ? 'border-pass/50 bg-pass-wash font-semibold text-pass-deep'
                : 'border-rail bg-white text-ink-soft hover:bg-pass-wash/50 hover:text-ink'
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
            className="flex-1 rounded-[4px] border border-ink/25 bg-white px-3 py-2 text-sm text-ink placeholder:text-ink-mute focus:border-pass-deep focus:outline-none focus:ring-2 focus:ring-pass/30"
          />
          <button
            type="submit"
            className="shrink-0 rounded-[4px] border border-rail bg-white px-4 py-2 font-mono text-[12px] font-semibold uppercase tracking-[0.12em] text-ink transition-colors hover:bg-pass-wash"
          >
            Send
          </button>
        </form>
      )}

      <p className="mt-3 text-[11px] text-ink-mute">
        Anonymous, used only to improve this page. No email required.
      </p>
    </div>
  );
}
