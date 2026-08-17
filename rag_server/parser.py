from fastapi import HTTPException
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
import io
import csv
import json
import docx

def extract_text(file_bytes: bytes, fileName: str) -> str:
    ext = fileName.lower().split('.')[-1]
    text = ""
    try:
        if ext == 'pdf':
            reader = PdfReader(io.BytesIO(file_bytes))
            text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
        elif ext in ['doc', 'docx']:
            doc = docx.Document(io.BytesIO(file_bytes))
            text = "\n".join([para.text for para in doc.paragraphs])
        elif ext in ['csv', 'tsv']:
            content = file_bytes.decode("utf-8", errors='ignore')
            delimiter = '\t' if ext == 'tsv' else ','
            reader = csv.reader(io.StringIO(content), delimiter=delimiter)
            text = "\n".join([', '.join(row) for row in reader])
        elif ext == 'json':
            content = file_bytes.decode("utf-8", errors='ignore')
            try:
                text = json.dumps(json.loads(content), indent=2, ensure_ascii=False)
            except:
                text = content
        elif ext == 'xlsx':
            import pandas as pd
            df_dict = pd.read_excel(io.BytesIO(file_bytes), sheet_name=None)
            text_parts = []
            for sheet_name, df in df_dict.items():
                text_parts.append(f"--- Bảng: {sheet_name} ---")
                text_parts.append(df.to_markdown(index=False))
            text = "\n".join(text_parts)
        else:
            text = file_bytes.decode("utf-8", errors='ignore')
        if not text.strip():
            raise ValueError("Không có dữ liệu phù hợp để đọc")
    except Exception as e:
        print(f"Error extracting {fileName}: {e}")
        raise HTTPException(status_code=422, detail=f"Không thể đọc nội dung file {fileName}: {str(e)}")
    return text

def chunk_text(text: str) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size = 800,
        chunk_overlap = 150,
        separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
    )
    return splitter.split_text(text)
