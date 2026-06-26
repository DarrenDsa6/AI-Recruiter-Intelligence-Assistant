function SkillTag({ label, variant = "default" }) {
  const styles = {
    default: "bg-white/10 text-gray-300 border border-white/10",
    matched: "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30",
    missing: "bg-red-500/20 text-red-300 border border-red-500/30",
    required: "bg-blue-500/20 text-blue-300 border border-blue-500/30",
    optional: "bg-purple-500/20 text-purple-300 border border-purple-500/30",
  };

  return (
    <span className={`inline-block px-3 py-1 rounded-full text-xs font-medium ${styles[variant] || styles.default}`}>
      {typeof label === "string" ? label : label.name || JSON.stringify(label)}
    </span>
  );
}

export default function SkillsSection({ required, matched, missing }) {
  if (!required && !matched && !missing) return null;

  return (
    <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-6">
      <h3 className="text-sm font-semibold text-gray-300 mb-4">Skills Analysis</h3>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Required Skills */}
        <div className="bg-white/5 rounded-xl p-4">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-medium text-blue-300">Required</span>
            <span className="text-[10px] text-gray-500">{required?.length || 0} skills</span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {required?.length > 0 ? required.map((s, i) => (
              <SkillTag key={i} label={s} variant="required" />
            )) : <span className="text-xs text-gray-600">—</span>}
          </div>
        </div>

        {/* Matched Skills */}
        <div className="bg-white/5 rounded-xl p-4">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-medium text-emerald-300">Matched</span>
            <span className="text-[10px] text-gray-500">{matched?.length || 0} skills</span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {matched?.length > 0 ? matched.map((s, i) => (
              <SkillTag key={i} label={s} variant="matched" />
            )) : <span className="text-xs text-gray-600">None</span>}
          </div>
        </div>

        {/* Missing Skills */}
        <div className="bg-white/5 rounded-xl p-4">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-medium text-red-300">Missing</span>
            <span className="text-[10px] text-gray-500">{missing?.length || 0} skills</span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {missing?.length > 0 ? missing.map((s, i) => (
              <SkillTag key={i} label={s} variant="missing" />
            )) : <span className="text-xs text-gray-600">None</span>}
          </div>
        </div>
      </div>
    </div>
  );
}
