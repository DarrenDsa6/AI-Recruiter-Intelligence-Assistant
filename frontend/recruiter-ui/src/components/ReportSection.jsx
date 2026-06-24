function BulletList({ items, icon, color }) {
  if (!items || items.length === 0) return null;
  return (
    <ul className="space-y-1.5">
      {items.map((item, i) => (
        <li key={i} className="flex items-start gap-2 text-sm">
          <span className={`mt-0.5 shrink-0 ${color}`}>{icon}</span>
          <span className="text-gray-300">{item}</span>
        </li>
      ))}
    </ul>
  );
}

export default function ReportSection({ report }) {
  if (!report) return null;

  return (
    <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-6">
      <h3 className="text-sm font-semibold text-gray-300 mb-4">AI Report</h3>

      <div className="space-y-4">
        {report.summary && (
          <div className="bg-white/5 rounded-xl p-4">
            <p className="text-sm text-gray-400 leading-relaxed">{report.summary}</p>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {report.strengths?.length > 0 && (
            <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-4">
              <h4 className="text-xs font-semibold text-emerald-400 uppercase tracking-wider mb-3">Strengths</h4>
              <BulletList
                items={report.strengths}
                icon="+"
                color="text-emerald-400"
              />
            </div>
          )}

          {report.weaknesses?.length > 0 && (
            <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4">
              <h4 className="text-xs font-semibold text-red-400 uppercase tracking-wider mb-3">Weaknesses</h4>
              <BulletList
                items={report.weaknesses}
                icon="−"
                color="text-red-400"
              />
            </div>
          )}
        </div>

        {report.recommendation && (
          <div className="bg-blue-500/10 border border-blue-500/20 rounded-xl p-4">
            <h4 className="text-xs font-semibold text-blue-400 uppercase tracking-wider mb-2">Recommendation</h4>
            <p className="text-sm text-blue-300/90">{report.recommendation}</p>
          </div>
        )}

        {report.authenticity_score !== undefined && (
          <div className="flex items-center gap-2 justify-end">
            <span className="text-xs text-gray-500">Authenticity:</span>
            <span className={`text-xs font-semibold ${
              report.authenticity_score >= 7 ? "text-emerald-400" :
              report.authenticity_score >= 4 ? "text-amber-400" :
              "text-red-400"
            }`}>
              {report.authenticity_score}/10
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
