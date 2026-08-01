export default function GithubSection({ data }) {
  if (!data) return null;

  const summary = typeof data.summary === "string" ? data.summary : "";
  const stats = [
    { label: "Repositories", value: data.repo_count ?? "—" },
    { label: "Total Stars", value: data.total_stars ?? "—" },
    { label: "Total Forks", value: data.total_forks ?? "—" },
    { label: "With READMEs", value: data.has_readme_ratio ?? "—" },
  ];
  const languages = Array.isArray(data.top_languages) ? data.top_languages : [];
  const llm =
    data.llm_analysis && typeof data.llm_analysis === "object" && !data.llm_analysis.error
      ? data.llm_analysis
      : null;
  const strengths = llm && Array.isArray(llm.strengths) ? llm.strengths : [];
  const weaknesses = llm && Array.isArray(llm.weaknesses) ? llm.weaknesses : [];

  return (
    <section className="card animate-slide-up !p-0 overflow-hidden" style={{ animationDelay: "360ms" }}>
      <div className="flex items-center gap-3 border-b border-white/[0.06] px-5 py-4">
        <span className="icon-tile">
          <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 0C5.37 0 0 5.37 0 12c0 5.3 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61-.546-1.385-1.335-1.755-1.335-1.755-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 21.795 24 17.295 24 12 24 5.37 18.63 0 12 0z"/>
          </svg>
        </span>
        <div>
          <h3 className="text-sm font-semibold text-neutral-100">GitHub Insights</h3>
          <p className="text-[11px] text-neutral-500">Signals derived from your public repositories</p>
        </div>
      </div>

      <div className="space-y-3 p-5">
        {summary && (
          <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-4">
            <p className="text-sm leading-relaxed text-neutral-300">{summary}</p>
          </div>
        )}

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {stats.map((s) => (
            <div key={s.label} className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-4">
              <span className="mb-1 block text-[10px] font-semibold uppercase tracking-widest text-neutral-500">
                {s.label}
              </span>
              <span className="text-sm font-medium text-neutral-200">{s.value}</span>
            </div>
          ))}
        </div>

        {languages.length > 0 && (
          <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-4">
            <span className="mb-2 block text-[10px] font-semibold uppercase tracking-widest text-neutral-500">
              Top Languages
            </span>
            <div className="flex flex-wrap gap-2">
              {languages.map((lang, i) => (
                <span key={i} className="chip !text-[11px]">
                  {lang}
                </span>
              ))}
            </div>
          </div>
        )}

        {llm && (
          <div className="space-y-3 rounded-xl border border-white/[0.06] bg-white/[0.02] p-4">
            <div className="flex flex-wrap items-center gap-2">
              {llm.overall_score != null && (
                <span className="chip border-primary-400/30 bg-primary-500/10 text-primary-300">
                  Overall: {llm.overall_score}
                </span>
              )}
              {llm.complexity_rating && (
                <span className="chip">Complexity: {llm.complexity_rating}</span>
              )}
            </div>
            {typeof llm.summary === "string" && llm.summary && (
              <p className="text-sm leading-relaxed text-neutral-300">{llm.summary}</p>
            )}
            {strengths.length > 0 && (
              <div className="rounded-xl border border-success-500/20 bg-success-500/[0.06] p-4">
                <span className="mb-2.5 block text-xs font-semibold text-success-400">Strengths</span>
                <ul className="space-y-1.5">
                  {strengths.map((s, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-neutral-300">
                      <span className="mt-0.5 font-semibold text-success-400">+</span>
                      <span>{typeof s === "string" ? s : s.signal || JSON.stringify(s)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {weaknesses.length > 0 && (
              <div className="rounded-xl border border-danger-500/20 bg-danger-500/[0.06] p-4">
                <span className="mb-2.5 block text-xs font-semibold text-danger-400">Weaknesses</span>
                <ul className="space-y-1.5">
                  {weaknesses.map((s, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-neutral-300">
                      <span className="mt-0.5 font-semibold text-danger-400">−</span>
                      <span>{typeof s === "string" ? s : s.signal || JSON.stringify(s)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
