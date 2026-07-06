export function toList(v) {
  return Array.isArray(v) ? v : (v ? [v] : []);
}

export function renderItem(item) {
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
      if (item.details) return item.category + ": " + (Array.isArray(item.details) ? item.details.join("; ") : item.details);
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

export function normalizeScore(n) {
  if (typeof n === "number") return n > 10 ? Math.round(n / 10) : Math.round(n);
  if (typeof n === "object" && n !== null && typeof n.score === "number") return normalizeScore(n.score);
  return 0;
}
