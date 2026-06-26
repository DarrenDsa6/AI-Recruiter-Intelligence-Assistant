export default function QuestionsPanel({ questions }) {
  return (
    <div className="bg-gray-800 p-6 rounded-xl shadow">
      <h2 className="text-xl mb-4">Interview Questions</h2>

      <h3 className="font-semibold">Technical</h3>
      <ul className="list-disc ml-5 mb-4">
        {questions.technical?.slice(0, 5).map((q, i) => (
          <li key={i}>{typeof q === "string" ? q : q.question || q.name || JSON.stringify(q)}</li>
        ))}
      </ul>

      <h3 className="font-semibold">Behavioral</h3>
      <ul className="list-disc ml-5">
        {questions.behavioral?.slice(0, 5).map((q, i) => (
          <li key={i}>{typeof q === "string" ? q : q.question || q.name || JSON.stringify(q)}</li>
        ))}
      </ul>
    </div>
  );
}