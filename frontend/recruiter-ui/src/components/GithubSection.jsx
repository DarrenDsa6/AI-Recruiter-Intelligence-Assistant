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

export default function GithubSection({ data }) {
  if (!data) return null;

  const summary = data.summary || data;
  const signals = data.signals || {};
  const strong = signals.strong || [];
  const weak = signals.weak || [];

  return (
    <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-6">
      <div className="flex items-center gap-2 mb-4">
        <svg className="w-5 h-5 text-gray-400" fill="currentColor" viewBox="0 0 24 24">
          <path d="M12 0C5.37 0 0 5.37 0 12c0 5.3 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61-.546-1.385-1.335-1.755-1.335-1.755-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 21.795 24 17.295 24 12 24 5.37 18.63 0 12 0z"/>
        </svg>
        <h3 className="text-sm font-semibold text-gray-300">GitHub Insights</h3>
      </div>

      <div className="space-y-3">
        <div className="bg-white/5 rounded-xl p-4">
          <p className="text-sm text-gray-400 leading-relaxed">
            {typeof summary === "string" ? summary : JSON.stringify(summary)}
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {data.skill_level && (
            <div className="bg-white/5 rounded-xl p-4">
              <span className="text-xs text-gray-500 block mb-1">Skill Level</span>
              <span className="text-sm font-medium text-gray-200">{renderItem(data.skill_level)}</span>
            </div>
          )}
          {data.best_project && (
            <div className="bg-white/5 rounded-xl p-4">
              <span className="text-xs text-gray-500 block mb-1">Best Project</span>
              <span className="text-sm font-medium text-gray-200">{renderItem(data.best_project)}</span>
            </div>
          )}
        </div>

        {strong.length > 0 && (
          <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-4">
            <span className="text-xs font-medium text-emerald-400 block mb-2">Strong Signals</span>
            <ul className="space-y-1">
              {strong.map((s, i) => (
                <li key={i} className="text-sm text-emerald-300/80 flex items-start gap-2">
                  <span className="mt-0.5">+</span>
                  <span>{renderItem(s)}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {weak.length > 0 && (
          <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4">
            <span className="text-xs font-medium text-red-400 block mb-2">Weak Signals</span>
            <ul className="space-y-1">
              {weak.map((s, i) => (
                <li key={i} className="text-sm text-red-300/80 flex items-start gap-2">
                  <span className="mt-0.5">−</span>
                  <span>{renderItem(s)}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
