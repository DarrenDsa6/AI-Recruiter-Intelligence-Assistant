function renderItem(item) {
  if (typeof item === "string") return item;
  if (typeof item === "object" && item !== null) {
    if (item.category) {
      if (item.details?.length) return item.category + ": " + item.details.join("; ");
      let text = item.category;
      if (item.skills?.length) text += " — " + item.skills.join(", ");
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

export default function ReportCard({ report }) {
  return (
    <div className="bg-gray-800 p-6 rounded-xl shadow">
      <h2 className="text-xl mb-4">AI Report</h2>

      <p className="mb-3">{report.summary}</p>

      <h3 className="mt-4 font-semibold">Strengths</h3>
      <ul className="list-disc ml-5">
        {report.strengths?.map((s, i) => (
          <li key={i}>{renderItem(s)}</li>
        ))}
      </ul>

      <h3 className="mt-4 font-semibold">Weaknesses</h3>
      <ul className="list-disc ml-5">
        {report.weaknesses?.map((w, i) => (
          <li key={i}>{renderItem(w)}</li>
        ))}
      </ul>
    </div>
  );
}