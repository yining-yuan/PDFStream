"""
PDF processing module for PDFStream
Handles PDF text extraction and keyword extraction
"""

import os
from typing import List, Dict, Tuple
import PyPDF2
import re
from collections import Counter
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize


class PDFProcessor:
    """Handles PDF text extraction and keyword extraction"""
    
    def __init__(self):
        """Initialize PDF processor and download required NLTK data"""
        self._ensure_nltk_data()
        try:
            self.stop_words = set(stopwords.words('english'))
        except LookupError:
            self._ensure_nltk_data()
            self.stop_words = set(stopwords.words('english'))
    
    def _ensure_nltk_data(self):
        """Ensure required NLTK data is downloaded"""
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt', quiet=True)
        
        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('stopwords', quiet=True)
    
    def extract_text_from_pdf(self, pdf_path: str) -> Tuple[str, int]:
        """
        Extract text content from a PDF file
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Tuple of (extracted_text, page_count)
        """
        text = ""
        page_count = 0
        
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                page_count = len(pdf_reader.pages)
                
                for page in pdf_reader.pages:
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                    except Exception as e:
                        print(f"Error extracting text from page: {e}")
                        continue
        except Exception as e:
            print(f"Error reading PDF file: {e}")
            raise
        
        return text.strip(), page_count
    
    def extract_keywords(self, text: str, top_n: int = 50) -> List[str]:
        """
        Extract keywords from text using frequency analysis
        
        Args:
            text: Input text
            top_n: Number of top keywords to return
            
        Returns:
            List of keywords
        """
        # Convert to lowercase and remove special characters
        text = text.lower()
        text = re.sub(r'[^a-z0-9\s]', ' ', text)
        
        # Tokenize
        try:
            tokens = word_tokenize(text)
        except Exception:
            # Fallback to simple split if word_tokenize fails
            tokens = text.split()
        
        # Filter out stop words and short words
        filtered_tokens = [
            word for word in tokens 
            if word not in self.stop_words 
            and len(word) > 2
            and not word.isdigit()
        ]
        
        # Count frequencies
        word_freq = Counter(filtered_tokens)
        
        # Get top N keywords
        keywords = [word for word, _ in word_freq.most_common(top_n)]
        
        return keywords
    
    def process_pdf(self, pdf_path: str, top_keywords: int = 50) -> Dict:
        """
        Process a PDF file: extract text and keywords
        
        Args:
            pdf_path: Path to the PDF file
            top_keywords: Number of top keywords to extract
            
        Returns:
            Dictionary with extracted data
        """
        # Extract text
        text, page_count = self.extract_text_from_pdf(pdf_path)
        
        # Extract keywords
        keywords = self.extract_keywords(text, top_keywords)
        
        # Get file info
        file_size = os.path.getsize(pdf_path)
        filename = os.path.basename(pdf_path)
        
        return {
            'filename': filename,
            'filepath': pdf_path,
            'text': text,
            'keywords': keywords,
            'page_count': page_count,
            'file_size': file_size
        }
    
    def extract_keywords_from_text(self, text: str, top_n: int = 20) -> List[str]:
        """
        Extract keywords from raw text (for search queries)
        
        Args:
            text: Input text
            top_n: Number of keywords to return
            
        Returns:
            List of keywords
        """
        return self.extract_keywords(text, top_n)
