export default function ScoreCard({ score }) {
  let color = "text-red-400";

  if (score > 70) color = "text-green-400";
  else if (score > 40) color = "text-yellow-400";

  return (
    <div className="bg-gray-800 p-6 rounded-xl shadow-lg">
      <h2 className="text-lg mb-2">Match Score</h2>

      <div className={`text-5xl font-bold ${color}`}>
        {score}%
      </div>

      <div className="w-full bg-gray-700 h-2 mt-4 rounded">
        <div
          className="bg-green-500 h-2 rounded"
          style={{ width: `${score}%` }}
        />
      </div>
    </div>
  );
}