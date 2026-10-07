import { useState } from 'react';
import { FileUp, Link2, ScanLine, ClipboardPaste, Tag, Asterisk, Sparkles, Square } from 'lucide-react';
import Layout from '../components/Layout';
import RiskBadge from '../components/RiskBadge';
import RedactedPreview, { RedactionMode } from '../components/RedactedPreview';
import { api } from '../lib/api';

const REDACTION_OPTIONS: { id: RedactionMode; label: string; icon: any; sample: string }[] = [
  { id: 'tagged', label: 'Tagged', icon: Tag, sample: '[EMAIL REDACTED]' },
  { id: 'mask', label: 'Masked', icon: Asterisk, sample: 'joh******@gmail.com' },
  { id: 'synthetic', label: 'Synthetic', icon: Sparkles, sample: 'user.sample@example.com' },
  { id: 'blackout', label: 'Blackout', icon: Square, sample: '████████' },
];

export default function Scan() {
  const [tab, setTab] = useState<'text' | 'document' | 'url'>('text');
  const [text, setText] = useState('');
  const [url, setUrl] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [redactionMode, setRedactionMode] = useState<RedactionMode>('tagged');
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function run() {
    setBusy(true);
    setError('');
    setResult(null);
    try {
      const r =
        tab === 'text'
          ? await api.text(text, redactionMode)
          : tab === 'url'
          ? await api.url(url, redactionMode)
          : await api.document(file!, redactionMode);
      setResult(r.analysis);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Layout>
      <div className="p-5 md:p-8 max-w-6xl mx-auto">
        <div className="mb-7">
          <p className="text-cyan-300 text-sm font-semibold">Privacy analysis</p>
          <h1 className="text-3xl font-bold">New scan</h1>
          <p className="text-slate-400 mt-2">Analyze text, documents, or URLs for sensitive-data exposure.</p>
        </div>

        <div className="grid lg:grid-cols-[1.15fr_.85fr] gap-6">
          <section className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
            <div className="flex gap-2 mb-5">
              {[
                ['text', 'Text', ClipboardPaste],
                ['document', 'Document', FileUp],
                ['url', 'URL', Link2],
              ].map(([id, label, Icon]: any) => (
                <button
                  key={id}
                  onClick={() => setTab(id)}
                  className={`flex-1 py-2.5 rounded-xl text-sm font-semibold flex justify-center items-center gap-2 transition-colors ${
                    tab === id ? 'bg-cyan-400 text-slate-950 font-bold' : 'bg-slate-950 text-slate-400 border border-slate-800 hover:text-slate-200'
                  }`}
                >
                  <Icon size={16} />
                  {label}
                </button>
              ))}
            </div>

            {tab === 'text' && (
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Paste content here… e.g. 'Upload your Aadhaar, PAN, bank account details and OTP'"
                className="w-full h-72 resize-none bg-slate-950 border border-slate-800 rounded-xl p-4 outline-none focus:border-cyan-400 text-sm leading-6"
              />
            )}

            {tab === 'url' && (
              <div>
                <label className="text-sm text-slate-400">URL to analyze</label>
                <input
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://example.com/account?email=test@example.com"
                  className="w-full mt-2 bg-slate-950 border border-slate-800 rounded-xl p-4 outline-none focus:border-cyan-400"
                />
                <p className="text-xs text-slate-500 mt-3">
                  The baseline analyzes the URL itself and its query/path signals; it does not execute JavaScript or submit credentials.
                </p>
              </div>
            )}

            {tab === 'document' && (
              <label className="h-72 border-2 border-dashed border-slate-700 rounded-xl flex flex-col items-center justify-center cursor-pointer hover:border-cyan-400 transition-colors">
                <FileUp size={34} className="text-cyan-300 mb-3" />
                <span className="font-semibold px-4 text-center">{file ? file.name : 'Choose TXT, CSV, JSON, PDF, DOCX or an image'}</span>
                <span className="text-xs text-slate-500 mt-2">Maximum 5 MB · OCR supported for images and scanned PDFs</span>
                <input
                  type="file"
                  className="hidden"
                  accept=".txt,.csv,.json,.pdf,.docx,.png,.jpg,.jpeg,.webp,.bmp,.tiff"
                  onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                />
              </label>
            )}

            {/* Redaction Style Selector */}
            <div className="mt-5 pt-5 border-t border-slate-800/80">
              <label className="block text-xs font-semibold text-slate-400 mb-2.5">
                Preferred Redaction Style
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {REDACTION_OPTIONS.map((opt) => {
                  const Icon = opt.icon;
                  const selected = redactionMode === opt.id;
                  return (
                    <button
                      key={opt.id}
                      type="button"
                      onClick={() => setRedactionMode(opt.id)}
                      className={`p-2.5 rounded-xl border text-left flex flex-col justify-between transition-all ${
                        selected
                          ? 'border-cyan-400 bg-cyan-400/10 text-cyan-200'
                          : 'border-slate-800 bg-slate-950 text-slate-400 hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-center gap-1.5 mb-1">
                        <Icon size={13} className={selected ? 'text-cyan-300' : 'text-slate-500'} />
                        <span className="text-xs font-semibold">{opt.label}</span>
                      </div>
                      <span className="text-[10px] text-slate-500 truncate font-mono">{opt.sample}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {error && <div className="mt-4 p-3 rounded-xl bg-red-500/10 text-red-300 text-sm">{error}</div>}

            <button
              disabled={busy || (tab === 'text' && !text.trim()) || (tab === 'url' && !url.trim()) || (tab === 'document' && !file)}
              onClick={run}
              className="w-full mt-5 py-3 rounded-xl bg-cyan-400 text-slate-950 font-bold disabled:opacity-40 flex items-center justify-center gap-2 transition-opacity"
            >
              <ScanLine size={18} />
              {busy ? 'Analyzing…' : 'Analyze privacy risk'}
            </button>
          </section>

          <section className="bg-slate-900 border border-slate-800 rounded-2xl p-5 min-h-[480px]">
            {!result ? (
              <div className="h-full flex flex-col items-center justify-center text-center text-slate-500 py-16">
                <ShieldIcon />
                <h2 className="text-white font-semibold mt-4">Analysis results</h2>
                <p className="text-sm mt-2 max-w-sm">Your risk score, detected PII, explanations and customizable redaction preview will appear here.</p>
              </div>
            ) : (
              <Result result={result} defaultMode={redactionMode} />
            )}
          </section>
        </div>
      </div>
    </Layout>
  );
}

function ShieldIcon() {
  return (
    <div className="w-14 h-14 rounded-2xl bg-cyan-400/10 text-cyan-300 flex items-center justify-center">
      <ScanLine />
    </div>
  );
}

function Result({ result, defaultMode }: { result: any; defaultMode: RedactionMode }) {
  const ex = result.explainability ?? {};
  const probs = ex.modelProbabilities ?? {};

  return (
    <div>
      <div className="flex justify-between items-start">
        <div>
          <p className="text-xs text-slate-500">Risk assessment</p>
          <div className="flex items-center gap-3 mt-2">
            <span className="text-4xl font-bold">{result.riskScore}</span>
            <span className="text-slate-500">/100</span>
            <RiskBadge level={result.riskLevel} />
          </div>
          <p className="text-xs text-slate-500 mt-2">
            Model: {ex.model ?? 'trained classifier'} · Confidence: {Math.round((ex.modelConfidence ?? 0) * 100)}%
          </p>
        </div>
      </div>

      <div className="mt-5 p-3 bg-cyan-400/5 border border-cyan-400/10 rounded-xl text-xs text-slate-400">
        <span className="text-cyan-300 font-semibold">Extraction:</span> {result.documentIntelligence?.extractionMethod ?? 'text'}{' '}
        {result.documentIntelligence?.ocrUsed ? '· OCR used' : ''}
        {result.documentIntelligence?.pages?.length ? ` · ${result.documentIntelligence.pages.length} page(s)` : ''}
        {result.documentIntelligence?.pages?.some((p: any) => typeof p.ocrConfidence === 'number')
          ? ' · OCR confidence is extraction quality'
          : ''}
      </div>

      <div className="mt-7">
        <h3 className="font-semibold mb-3">Detected information</h3>
        {result.findings.length ? (
          <div className="space-y-2">
            {result.findings.map((f: any, i: number) => (
              <div key={i} className="flex justify-between gap-3 p-3 bg-slate-950 rounded-xl">
                <div>
                  <div className="text-sm font-semibold">{f.type}</div>
                  <div className="text-xs text-slate-500 mt-1">{f.valueMasked}</div>
                </div>
                <span className="text-xs text-slate-500">{Math.round(f.confidence * 100)}%</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-emerald-300">No high-confidence sensitive data detected.</p>
        )}
      </div>

      <div className="mt-7">
        <h3 className="font-semibold mb-3">Why this risk?</h3>
        <ul className="space-y-2 text-sm text-slate-400">
          {result.factors.map((x: string) => (
            <li key={x} className="flex gap-2">
              <span className="text-cyan-300">•</span>
              {x}
            </li>
          ))}
        </ul>
      </div>

      <div className="mt-7">
        <h3 className="font-semibold mb-3">Context signals</h3>
        <div className="space-y-2">
          {(ex.contextSignals ?? []).map((s: any, i: number) => (
            <div key={i} className="flex items-center justify-between p-3 bg-slate-950 rounded-xl">
              <div>
                <div className="text-sm font-semibold">{s.category.replace('_', ' ')}</div>
                <div className="text-xs text-slate-500 mt-1">
                  “{s.keyword}” — {s.label}
                </div>
              </div>
              <span className="text-xs text-cyan-300">+{s.weight}</span>
            </div>
          ))}
          {!(ex.contextSignals ?? []).length && (
            <p className="text-sm text-slate-500">No contextual risk signals detected.</p>
          )}
        </div>
      </div>

      <div className="mt-7">
        <h3 className="font-semibold mb-3">Model explanation</h3>
        <div className="p-4 bg-slate-950 rounded-xl space-y-2">
          <div className="flex justify-between text-xs text-slate-400">
            <span>LOW</span>
            <span>{Math.round((probs.LOW ?? 0) * 100)}%</span>
          </div>
          <div className="flex justify-between text-xs text-slate-400">
            <span>MEDIUM</span>
            <span>{Math.round((probs.MEDIUM ?? 0) * 100)}%</span>
          </div>
          <div className="flex justify-between text-xs text-slate-400">
            <span>HIGH</span>
            <span>{Math.round((probs.HIGH ?? 0) * 100)}%</span>
          </div>
          <div className="flex justify-between text-xs text-slate-400">
            <span>CRITICAL</span>
            <span>{Math.round((probs.CRITICAL ?? 0) * 100)}%</span>
          </div>
          {(ex.narrative ?? []).map((x: string, i: number) => (
            <p key={i} className="text-xs text-slate-400 pt-2 border-t border-slate-800">
              {x}
            </p>
          ))}
        </div>
      </div>

      <div className="mt-7">
        <h3 className="font-semibold mb-3">Recommendations</h3>
        <ul className="space-y-2 text-sm text-slate-400">
          {result.recommendations.map((x: string) => (
            <li key={x} className="flex gap-2">
              <span className="text-emerald-300">✓</span>
              {x}
            </li>
          ))}
        </ul>
      </div>

      {/* Redacted Preview with interactive mode toggle and copy */}
      <RedactedPreview
        defaultText={result.redactedText}
        variations={result.redactedVariations}
        initialMode={result.redactionMode || defaultMode}
      />
    </div>
  );
}
