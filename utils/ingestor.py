import requests
from bs4 import BeautifulSoup
import PyPDF2
from docx import Document

class UniversalIngestor:
    def __init__(self, source_path):
        self.source_path = source_path
        self.content = ""
        self.metadata = {"origin": source_path}

    def get_ingest_payload(self, file_object=None):
        # 1. Handle URLs (with User-Agent to avoid 'Robot' errors)
        if self.source_path.startswith("http"):
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                response = requests.get(self.source_path, headers=headers, timeout=10)
                
                if response.status_code == 403:
                    self.content = "Error: Access Denied. The website is blocking our scraper."
                    return {"raw_text": self.content, "metadata": self.metadata}

                soup = BeautifulSoup(response.content, 'html.parser')
                for s in soup(["script", "style", "nav", "header", "footer"]):
                    s.decompose()
                
                self.content = (soup.find('main') or soup.body).get_text(separator=' ', strip=True)
                self.metadata["type"] = "URL"
            except Exception as e:
                self.content = f"URL Error: {e}"
        
        # 2. Handle PDFs
        elif file_object and file_object.name.endswith(".pdf"):
            try:
                reader = PyPDF2.PdfReader(file_object)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + " "
                self.content = text.strip()
                self.metadata["type"] = "PDF"
            except Exception as e:
                self.content = f"PDF Error: {e}"

        # 3. Handle Word Docs
        elif file_object and file_object.name.endswith(".docx"):
            try:
                doc = Document(file_object)
                self.content = " ".join([p.text for p in doc.paragraphs])
                self.metadata["type"] = "DOCX"
            except Exception as e:
                self.content = f"DOCX Error: {e}"

        return {"raw_text": self.content, "metadata": self.metadata}