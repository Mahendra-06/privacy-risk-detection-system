import { useState } from 'react';
import { Copy, Check, Tag, Asterisk, Sparkles, Square } from 'lucide-react';

export type RedactionMode = 'tagged' | 'mask' | 'synthetic' | 'blackout';

interface RedactedPreviewProps {
  initialMode?: RedactionMode;
  defaultText: string;
  variations?: Record<string, string>;
  title?: string;
}

const MODES: { id: RedactionMode; label: string; icon: any; hint: string }[] = [
  { id: 'tagged', label: 'Tagged', icon: Tag, hint: '[EMAIL REDACTED], [PHONE REDACTED]' },
  { id: 'mask', label: 'Masked', icon: Asterisk, hint: 'joh******@gmail.com, 98******10' },
  { id: 'synthetic', label: 'Synthetic', icon: Sparkles, hint: 'user.sample@example.com (dummy data)' },
  { id: 'blackout', label: 'Blackout', icon: Square, hint: '████████ (block redaction)' },
];

export default function RedactedPreview({
  initialMode = 'tagged',
  defaultText,
  variations,
  title = 'Redacted preview'
}: RedactedPreviewProps) {
  const [mode, setMode] = useState<RedactionMode>(initialMode);
  const [copied, setCopied] = useState(false);

  const currentText = variations?.[mode] || defaultText;

  async function handleCopy() {
    if (!currentText) return;
    try {
      await navigator.clipboard.writeText(currentText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (e) {
      console.error('Failed to copy', e);
    }
  }

  return (
    <div className="mt-7">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
        <h3 className="font-semibold text-slate-100">{title}</h3>
        <button
          type="button"
          onClick={handleCopy}
          className="text-xs px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 flex items-center gap-1.5 transition-colors"
        >
          {copied ? (
            <>
              <Check size={14} className="text-emerald-400" />
              <span className="text-emerald-400 font-medium">Copied!</span>
            </>
          ) : (
            <>
              <Copy size={14} className="text-slate-400" />
              <span>Copy text</span>
            </>
          )}
        </button>
      </div>

      {variations && (
        <div className="flex flex-wrap gap-1.5 p-1 bg-slate-950/80 border border-slate-800 rounded-xl mb-3">
          {MODES.map((m) => {
            const Icon = m.icon;
            const active = mode === m.id;
            return (
              <button
                key={m.id}
                type="button"
                onClick={() => setMode(m.id)}
                title={m.hint}
                className={`flex-1 min-w-[90px] py-1.5 px-2.5 rounded-lg text-xs font-medium flex items-center justify-center gap-1.5 transition-all ${
                  active
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900 border border-transparent'
                }`}
              >
                <Icon size={13} />
                <span>{m.label}</span>
              </button>
            );
          })}
        </div>
      )}

      <pre className="whitespace-pre-wrap font-mono text-xs leading-5 bg-slate-950 border border-slate-800/80 p-4 rounded-xl text-slate-300 max-h-56 overflow-auto selection:bg-cyan-500/30 selection:text-cyan-200">
        {currentText || 'No text to display.'}
      </pre>

      <p className="text-[11px] text-slate-500 mt-2">
        Style: <span className="text-cyan-300 font-medium">{MODES.find(m => m.id === mode)?.label}</span> &mdash; {MODES.find(m => m.id === mode)?.hint}
      </p>
    </div>
  );
}
