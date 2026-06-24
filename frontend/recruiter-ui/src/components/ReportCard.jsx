export default function ReportCard({ report }) {
  return (
    <div className="bg-gray-800 p-6 rounded-xl shadow">
      <h2 className="text-xl mb-4">AI Report</h2>

      <p className="mb-3">{report.summary}</p>

      <h3 className="mt-4 font-semibold">Strengths</h3>
      <ul className="list-disc ml-5">
        {report.strengths?.map((s, i) => (
          <li key={i}>{s}</li>
        ))}
      </ul>

      <h3 className="mt-4 font-semibold">Weaknesses</h3>
      <ul className="list-disc ml-5">
        {report.weaknesses?.map((w, i) => (
          <li key={i}>{w}</li>
        ))}
      </ul>
    </div>
  );
}