import os
import pandas as pd
import docx
import PyPDF2
import easyocr
from PIL import Image

def load_file(file_path: str) -> str:
    """
    Extract all text from a file based on its extension.
    Supports: .csv, .xlsx, .docx, .pdf, .txt, .png, .jpg, .jpeg
    """
    ext = os.path.splitext(file_path)[1].lower()
    text = ""

    if ext == '.csv':
        df = pd.read_csv(file_path)
        text = df.to_string(index=False)
    elif ext == '.xlsx':
        df = pd.read_excel(file_path, engine='openpyxl')
        text = df.to_string(index=False)
    elif ext == '.docx':
        doc = docx.Document(file_path)
        text = "\n".join([para.text for para in doc.paragraphs])
    elif ext == '.pdf':
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() or ""
    elif ext == '.txt':
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
    elif ext in ['.png', '.jpg', '.jpeg']:
        reader = easyocr.Reader(['en'])
        result = reader.readtext(file_path, detail=0)
        text = " ".join(result)
    else:
        raise ValueError(f"Unsupported file type: {ext}")

    return text.strip()