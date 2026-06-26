function toList(v) {
  return Array.isArray(v) ? v : (v ? [v] : []);
}

function renderItem(item) {
  if (typeof item === "string") return item;
  if (typeof item === "object" && item !== null) {
    if (item.signal) {
      const evidence = toList(item.evidence).length ? ": " + toList(item.evidence).join(" ") : "";
      return item.signal + evidence;
    }
    if (item.project) {
      let text = item.project;
      if (item.skills?.length) text += " — " + toList(item.skills).join(", ");
      if (item.details) text += ": " + (Array.isArray(item.details) ? item.details.join("; ") : item.details);
      if (item.minor_issue) text += " (issue: " + item.minor_issue + ")";
      if (item.positive) text += " — " + item.positive;
      return text;
    }
    if (item.category) {
      if (item.details) return item.category + ": " + (Array.isArray(item.details) ? item.details.join("; ") : item.details);
      let text = item.category;
      if (item.skills?.length) text += " — " + toList(item.skills).join(", ");
      if (item.projects?.length) text += " (projects: " + toList(item.projects).join(", ") + ")";
      if (item.observation) text += " — " + item.observation;
      return text;
    }
    if (item.status || item.next_steps || item.justification) {
      const parts = [];
      if (item.status) parts.push(item.status);
      if (item.next_steps) parts.push("Next: " + item.next_steps);
      if (item.justification) parts.push(item.justification);
      return parts.join(" — ");
    }
    return item.name || item.action || item.description || item.title || item.text || JSON.stringify(item);
  }
  return String(item);
}

function normalizeScore(n) {
  if (typeof n === "number") return n > 10 ? Math.round(n / 10) : Math.round(n);
  if (typeof n === "object" && n !== null && typeof n.score === "number") return normalizeScore(n.score);
  return 0;
}

function BulletList({ items, icon, color }) {
  if (!items || items.length === 0) return null;
  return (
    <ul className="space-y-1.5">
      {items.map((item, i) => (
        <li key={i} className="flex items-start gap-2 text-sm">
          <span className={`mt-0.5 shrink-0 ${color}`}>{icon}</span>
          <span className="text-gray-300">{renderItem(item)}</span>
        </li>
      ))}
    </ul>
  );
}

export default function ReportSection({ report }) {
  if (!report) return null;

  const authScore = typeof report.authenticity_score === "number"
    ? normalizeScore(report.authenticity_score)
    : null;

  return (
    <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-6">
      <h3 className="text-sm font-semibold text-gray-300 mb-4">AI Report</h3>

      <div className="space-y-4">
        {report.summary && (
          <div className="bg-white/5 rounded-xl p-4">
            <p className="text-sm text-gray-400 leading-relaxed">{renderItem(report.summary)}</p>
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
            <p className="text-sm text-blue-300/90">{renderItem(report.recommendation)}</p>
          </div>
        )}

        {authScore !== null && (
          <div className="flex items-center gap-2 justify-end">
            <span className="text-xs text-gray-500">Authenticity:</span>
            <span className={`text-xs font-semibold ${
              authScore >= 7 ? "text-emerald-400" :
              authScore >= 4 ? "text-amber-400" :
              "text-red-400"
            }`}>
              {authScore}/10
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
