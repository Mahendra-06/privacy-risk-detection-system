import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import Layout from '../components/Layout';
import RiskBadge from '../components/RiskBadge';
import RedactedPreview from '../components/RedactedPreview';
import { api } from '../lib/api';

export default function History() {
  const { id } = useParams();
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    (id ? api.scan(id) : api.scans()).then(setData).catch(console.error);
  }, [id]);

  if (id) {
    return (
      <Layout>
        <div className="p-5 md:p-8 max-w-5xl mx-auto">
          {data && (
            <>
              <Link to="/history" className="text-cyan-300 text-sm hover:underline">
                &larr; Back to history
              </Link>
              <div className="mt-6 bg-slate-900 border border-slate-800 rounded-2xl p-6">
                <div className="flex justify-between items-start">
                  <div>
                    <h1 className="text-2xl font-bold">{data.sourceName}</h1>
                    <p className="text-slate-500 text-sm mt-1">{new Date(data.createdAt).toLocaleString()}</p>
                  </div>
                  <RiskBadge level={data.riskLevel} />
                </div>
                <div className="mt-7 grid md:grid-cols-2 gap-5">
                  <div>
                    <h3 className="font-semibold mb-3">Risk score</h3>
                    <div className="text-5xl font-bold">
                      {data.riskScore}
                      <span className="text-lg text-slate-500">/100</span>
                    </div>
                  </div>
                  <div>
                    <h3 className="font-semibold mb-3">Findings</h3>
                    <div className="space-y-2">
                      {data.findings?.map((f: any, i: number) => (
                        <div key={i} className="p-3 bg-slate-950 rounded-xl text-sm flex justify-between items-center">
                          <b>{f.type}</b>
                          <span className="text-slate-500 font-mono text-xs">{f.valueMasked}</span>
                        </div>
                      ))}
                      {!data.findings?.length && (
                        <p className="text-xs text-slate-500">No sensitive findings in this scan.</p>
                      )}
                    </div>
                  </div>
                </div>
                <div className="mt-7">
                  <h3 className="font-semibold mb-3">Factors</h3>
                  <ul className="space-y-2 text-sm text-slate-400">
                    {data.factors?.map((x: string) => (
                      <li key={x}>&bull; {x}</li>
                    ))}
                  </ul>
                </div>

                {/* Interactive Redacted Preview */}
                <RedactedPreview
                  defaultText={data.redactedPreview}
                  variations={data.redactedVariations}
                  initialMode={data.redactionMode || 'tagged'}
                />
              </div>
            </>
          )}
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="p-5 md:p-8 max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold">Scan history</h1>
        <p className="text-slate-400 mt-2 mb-7">Previous privacy assessments for your account.</p>
        <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
          {data?.length ? (
            data.map((s: any) => (
              <Link
                to={`/history/${s._id}`}
                key={s._id}
                className="p-5 flex justify-between items-center border-b border-slate-800 last:border-0 hover:bg-slate-800/40 transition-colors"
              >
                <div>
                  <b className="text-slate-200">{s.sourceName}</b>
                  <div className="text-xs text-slate-500 mt-1">
                    {new Date(s.createdAt).toLocaleString()} &middot; {s.sourceType}
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-sm text-slate-500">{s.riskScore}/100</span>
                  <RiskBadge level={s.riskLevel} />
                </div>
              </Link>
            ))
          ) : (
            <div className="p-12 text-center text-slate-500">No scan history yet.</div>
          )}
        </div>
      </div>
    </Layout>
  );
}
