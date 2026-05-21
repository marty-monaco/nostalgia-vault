import urllib.parse
from bs4 import BeautifulSoup
import PyPDF2
from docx import Document

class UniversalIngestor:
    def __init__(self, source_input):
        self.source_input = source_input.strip()
        self.content = ""
        self.metadata = {"source_type": "unknown", "length": 0}

    def is_valid_url(self, url):
        try:
            result = urllib.parse.urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False

    def get_ingest_payload(self, file_object=None):
        # Scenario 1: It's an uploaded file (handled by app.py)
        if file_object is not None:
            self.content = "File processing handled at root."
            self.metadata["source_type"] = "file"
            
        # Scenario 2: It's an explicit website link
        elif self.is_valid_url(self.source_input) and (self.source_input.startswith("http://") or self.source_input.startswith("https://")):
            try:
                import requests
                headers = {'User-Agent': 'Mozilla/5.0'}
                response = requests.get(self.source_input, headers=headers, timeout=10)
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Strip script and style elements
                for script in soup(["script", "style"]):
                    script.extract()
                    
                self.content = soup.get_text(separator=' ')
                self.metadata["source_type"] = "url"
                self.metadata["url"] = self.source_input
            except Exception as e:
                self.content = f"Error scraping URL: {e}"
                
        # Scenario 3: Treat it as raw text paste (FAIL-SAFE)
        else:
            self.content = self.source_input
            self.metadata["source_type"] = "raw_text"

        # Clean up whitespace gaps
        chunks = [p.strip() for p in self.content.splitlines() if p.strip()]
        self.content = "\n".join(chunks)
        self.metadata["length"] = len(self.content)

        return {
            "raw_text": self.content,
            "metadata": self.metadata
        }
