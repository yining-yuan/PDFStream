# PDFStream - PDF Document Search and Matching System

## Overview
PDFStream is a system for managing and searching through large collections of PDF documents using keyword extraction and ML-based thematic matching.

## Features
- **PDF Upload and Processing**: Upload PDF documents and automatically extract text
- **Keyword Extraction**: Automatic extraction of relevant keywords from documents
- **Database Management**: SQLite-based storage for PDF metadata and keywords
- **ML-based Matching**: Find thematically similar documents using TF-IDF and cosine similarity
- **Web Interface**: User-friendly web UI for document management and search
- **REST API**: RESTful API for programmatic access

## Installation

1. Clone the repository:
```bash
git clone https://github.com/Yining0913/PDFStream.git
cd PDFStream
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python app.py
```

4. Access the web interface at `http://localhost:5000`

## Usage

### Upload Documents
1. Navigate to the web interface
2. Click "Upload PDF" and select one or more PDF files
3. The system will automatically extract text and keywords

### Search Documents
1. Upload a new document or enter search keywords
2. The system will find and rank similar documents
3. View detailed information about matched documents

### API Endpoints

- `GET /api/documents` - List all documents
- `POST /api/upload` - Upload a new PDF
- `POST /api/search` - Search for similar documents
- `GET /api/document/<id>` - Get document details
- `DELETE /api/document/<id>` - Delete a document

## Architecture

- **Backend**: Flask REST API
- **Database**: SQLite for metadata storage
- **ML Engine**: Scikit-learn (TF-IDF + Cosine Similarity)
- **PDF Processing**: PyPDF2 for text extraction
- **NLP**: NLTK for text processing and keyword extraction
- **Frontend**: HTML/CSS/JavaScript

## Requirements

See `requirements.txt` for Python dependencies.

## License

MIT License
