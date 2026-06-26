export default function SkillTags({ title, skills, color }) {
  return (
    <div className="bg-gray-800 p-5 rounded-xl shadow">
      <h3 className="mb-3">{title}</h3>

      <div className="flex flex-wrap gap-2">
        {skills.map((skill, i) => (
          <span
            key={i}
            className={`px-3 py-1 rounded text-sm ${color}`}
          >
            {typeof skill === "string" ? skill : skill.name || JSON.stringify(skill)}
          </span>
        ))}
      </div>
    </div>
  );
}