import re
import logging
from collections import OrderedDict
from config.constants import CHUNK_SIZE, CHUNK_OVERLAP

logger = logging.getLogger(__name__)

RESUME_SECTION_PATTERNS = [
    (r"(?i)(^|\n)(SUMMARY|PROFESSIONAL\s+SUMMARY|EXECUTIVE\s+SUMMARY|OBJECTIVE|CAREER\s+OBJECTIVE|PROFILE)\s*[\:\n]",
     "summary"),
    (r"(?i)(^|\n)(EXPERIENCE|WORK\s+EXPERIENCE|PROFESSIONAL\s+EXPERIENCE|EMPLOYMENT|WORK\s+HISTORY|CAREER\s+HISTORY|RELEVANT\s+EXPERIENCE)\s*[\:\n]",
     "experience"),
    (r"(?i)(^|\n)(EDUCATION|ACADEMIC|ACADEMIC\s+BACKGROUND|EDUCATIONAL\s+BACKGROUND|QUALIFICATIONS|CERTIFICATIONS?)\s*[\:\n]",
     "education"),
    (r"(?i)(^|\n)(SKILLS|TECHNICAL\s+SKILLS|CORE\s+COMPETENCIES|COMPETENCIES|EXPERTISE|TECHNOLOGIES|PROFICIENCIES|TOOLS|TECHNICAL\s+EXPERTISE)\s*[\:\n]",
     "skills"),
    (r"(?i)(^|\n)(PROJECTS|PROJECT\s+EXPERIENCE|KEY\s+PROJECTS|PROJECT\s+HIGHLIGHTS|PORTFOLIO|OPEN\s+SOURCE)\s*[\:\n]",
     "projects"),
    (r"(?i)(^|\n)(PUBLICATIONS|RESEARCH|RESEARCH\s+EXPERIENCE|THESIS|DISSERTATION)\s*[\:\n]",
     "publications"),
    (r"(?i)(^|\n)(AWARDS|HONORS|ACHIEVEMENTS|ACCOMPLISHMENTS|RECOGNITION)\s*[\:\n]",
     "awards"),
    (r"(?i)(^|\n)(LANGUAGES|LANGUAGE\s+PROFICIENCY)\s*[\:\n]",
     "languages"),
    (r"(?i)(^|\n)(VOLUNTEER|VOLUNTEERING|VOLUNTEER\s+EXPERIENCE|COMMUNITY|COMMUNITY\s+SERVICE)\s*[\:\n]",
     "volunteer"),
    (r"(?i)(^|\n)(REFERENCES?|REFEREES)\s*[\:\n]",
     "references"),
]


class SemanticChunker:
    """Chunks resume text into logical sections based on standard resume section headers."""

    def __init__(self):
        self.compiled_patterns = [
            (re.compile(pattern), label) for pattern, label in RESUME_SECTION_PATTERNS
        ]

    def detect_sections(self, text: str) -> OrderedDict:
        lines = text.split("\n")
        sections = OrderedDict()
        sections["preamble"] = []
        current_section = "preamble"

        for line in lines:
            matched_label = None
            for pattern, label in self.compiled_patterns:
                if pattern.match(line):
                    matched_label = label
                    break
            if matched_label:
                current_section = matched_label
                if current_section not in sections:
                    sections[current_section] = []
                continue

            sections.setdefault(current_section, []).append(line)

        result = OrderedDict()
        for key, val in sections.items():
            text_content = "\n".join(val).strip()
            if text_content:
                result[key] = text_content
        return result

    def chunk_text(self, text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[dict]:
        sections = self.detect_sections(text)
        chunks = []
        chunk_index = 0

        for section_name, section_text in sections.items():
            if len(section_text) <= chunk_size:
                chunks.append({
                    "text": section_text,
                    "start": 0,
                    "end": len(section_text),
                    "section": section_name,
                    "chunk_index": chunk_index,
                })
                chunk_index += 1
            else:
                start = 0
                while start < len(section_text):
                    end = min(start + chunk_size, len(section_text))
                    chunks.append({
                        "text": section_text[start:end],
                        "start": start,
                        "end": end,
                        "section": section_name,
                        "chunk_index": chunk_index,
                    })
                    chunk_index += 1
                    start += chunk_size - overlap

        logger.info(f"SemanticChunker: {len(sections)} sections -> {len(chunks)} chunks")
        return chunks


class BM25Index:
    """Simple BM25 index for keyword-based retrieval."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.documents: list[str] = []
        self.doc_freqs: list[dict[str, int]] = []
        self.inverted_index: dict[str, dict[int, int]] = {}
        self.avg_doc_len: float = 0.0
        self.total_docs: int = 0
        self.built = False

    def build(self, documents: list[str]):
        self.documents = documents
        self.total_docs = len(documents)
        total_len = 0
        self.doc_freqs = []
        self.inverted_index = {}

        for idx, doc in enumerate(documents):
            tokens = doc.lower().split()
            freq: dict[str, int] = {}
            for token in tokens:
                freq[token] = freq.get(token, 0) + 1
                if token not in self.inverted_index:
                    self.inverted_index[token] = {}
                self.inverted_index[token][idx] = self.inverted_index[token].get(idx, 0) + 1
            self.doc_freqs.append(freq)
            total_len += len(tokens)

        self.avg_doc_len = total_len / max(self.total_docs, 1)
        self.built = True

    def score(self, query: str, doc_idx: int) -> float:
        if not self.built:
            return 0.0
        tokens = query.lower().split()
        doc_len = sum(self.doc_freqs[doc_idx].values()) if doc_idx < len(self.doc_freqs) else 0
        score = 0.0

        for token in tokens:
            if token not in self.inverted_index:
                continue
            df = len(self.inverted_index[token])
            idf = ((self.total_docs - df + 0.5) / (df + 0.5) + 1.0) if df > 0 else 0
            tf = self.inverted_index[token].get(doc_idx, 0)
            if tf > 0:
                score += idf * ((tf * (self.k1 + 1)) / (tf + self.k1 * (1 - self.b + self.b * doc_len / self.avg_doc_len)))

        return score

    def search(self, query: str, top_k: int = 10) -> list[tuple[int, float]]:
        scores = []
        for idx in range(self.total_docs):
            s = self.score(query, idx)
            if s > 0:
                scores.append((idx, s))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


class ChunkerService:
    def __init__(self):
        self.semantic_chunker = SemanticChunker()

    def chunk_text(self, text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[dict]:
        if overlap >= chunk_size:
            raise ValueError("overlap must be less than chunk_size")
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunks.append({
                "text": text[start:end],
                "start": start,
                "end": end,
            })
            start += chunk_size - overlap
        return chunks

    def chunk_semantic(self, text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[dict]:
        return self.semantic_chunker.chunk_text(text, chunk_size, overlap)
