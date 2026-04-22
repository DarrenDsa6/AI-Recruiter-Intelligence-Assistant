import fitz  # PyMuPDF
from docx import Document
import os
import re

class DocumentParser:
    """
    Handles parsing of different document formats.
    Supports:
    - PDF
    - DOCX
    """

    @staticmethod
    def parse_pdf(file_path: str) -> str:
        """
        Extract text from PDF using PyMuPDF
        """
        text = ""

        try:
            doc = fitz.open(file_path)

            for page in doc:
                text += page.get_text()

            doc.close()

        except Exception as e:
            print(f"PDF parsing error: {e}")

        return text

    @staticmethod
    def parse_docx(file_path: str) -> str:
        """
        Extract text from DOCX using python-docx
        """
        text = ""

        try:
            doc = Document(file_path)

            paragraphs = [
                para.text
                for para in doc.paragraphs
                if para.text.strip()
            ]

            text = "\n".join(paragraphs)

        except Exception as e:
            print(f"DOCX parsing error: {e}")

        return text

    @staticmethod
    def clean_text(text: str) -> str:
        """
        Basic text cleaning
        Removes extra whitespace
        """
        text = re.sub(r"\s+", " ", text)
        text = text.strip()

        return text

    @staticmethod
    def parse(file_path: str) -> str:
        """
        Main router function
        Detect file type and parse accordingly
        """

        if not os.path.exists(file_path):
            raise FileNotFoundError(
                f"File not found: {file_path}"
            )

        if file_path.endswith(".pdf"):
            text = DocumentParser.parse_pdf(file_path)

        elif file_path.endswith(".docx"):
            text = DocumentParser.parse_docx(file_path)

        else:
            raise ValueError(
                "Unsupported file format. Use PDF or DOCX."
            )

        cleaned_text = DocumentParser.clean_text(text)

        return cleaned_text