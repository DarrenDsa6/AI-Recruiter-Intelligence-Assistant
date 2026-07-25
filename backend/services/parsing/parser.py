import tempfile
import os

import fitz
from docx import Document


class ParserService:
    def parse_file(self, file_bytes: bytes, filename: str) -> str:
        if filename.endswith(".pdf"):
            return self._parse_pdf(file_bytes)
        elif filename.endswith(".docx"):
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
            return "".join(page.get_text() for page in doc)
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
