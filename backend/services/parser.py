import fitz  # PyMuPDF
from docx import Document
import tempfile
import os

class ParserService:
    def parse_file(self, file_bytes, filename):
        if filename.endswith(".pdf"):
            return self.parse_pdf(file_bytes)

        elif filename.endswith(".docx"):
            return self.parse_docx(file_bytes)

        else:
            raise ValueError("Unsupported file type")

    def parse_pdf(self, file_bytes):
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                temp_file.write(file_bytes)
                temp_path = temp_file.name

            doc = fitz.open(temp_path)
            text = ""
            for page in doc:
                text += page.get_text()

            return text
        finally:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)

    def parse_docx(self, file_bytes):
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as temp_file:
                temp_file.write(file_bytes)
                temp_path = temp_file.name

            doc = Document(temp_path)
            text = ""

            for para in doc.paragraphs:
                text += para.text + "\n"

            return text
        finally:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)