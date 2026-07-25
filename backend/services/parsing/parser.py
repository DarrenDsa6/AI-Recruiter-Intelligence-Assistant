import tempfile
import os
import logging

import fitz
from docx import Document

from services.parsing.validator import validate_page_count

logger = logging.getLogger(__name__)


class ParserService:
    def parse_file(self, file_bytes: bytes, filename: str) -> str:
        if filename.lower().endswith(".pdf"):
            return self._parse_pdf(file_bytes)
        elif filename.lower().endswith(".docx"):
            return self._parse_docx(file_bytes)
        raise ValueError("Unsupported file type")

    def _parse_pdf(self, file_bytes: bytes) -> str:
        temp_path = None
        doc = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(file_bytes)
                temp_path = tmp.name
            doc = fitz.open(temp_path)
            validate_page_count(doc)
            lines = []
            for page in doc:
                blocks = page.get_text("blocks")
                blocks.sort(key=lambda b: (round(b[1] / 10) * 10, b[0]))
                for b in blocks:
                    text = b[4].strip()
                    if text:
                        lines.append(text)
            return "\n".join(lines)
        finally:
            if doc:
                doc.close()
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)

    def _parse_docx(self, file_bytes: bytes) -> str:
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
                tmp.write(file_bytes)
                temp_path = tmp.name
            doc = Document(temp_path)
            return "\n".join(para.text for para in doc.paragraphs)
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except PermissionError:
                    pass
