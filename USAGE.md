# PDFStream Usage Guide

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/Yining0913/PDFStream.git
cd PDFStream

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

Or use the startup script:
```bash
./start.sh
```

### 2. Access the Application

Open your web browser and navigate to:
```
http://localhost:5000
```

## Using the Web Interface

### Uploading Documents

1. **Drag and Drop**: Drag a PDF file onto the upload area
2. **Click to Select**: Click the upload area to open a file picker

Once uploaded, the system will:
- Extract all text from the PDF
- Generate keywords automatically
- Store the document in the database
- Make it searchable immediately

### Searching Documents

#### Method 1: Text Search
1. Enter keywords or paste text into the search box
2. Click "Search"
3. View matched documents ranked by similarity

#### Method 2: Find Similar Documents
1. Click on any document in the "All Documents" list
2. The system will find documents with similar content
3. Results are ranked by similarity score

### Understanding Results

- **Similarity Score**: Percentage indicating how similar documents are (0-100%)
- **Keywords**: Top keywords extracted from each document
- **Metadata**: Upload date, page count, and file size

## Using the API

See [API.md](API.md) for detailed API documentation.

### Quick Examples

#### Upload a PDF using cURL
```bash
curl -X POST http://localhost:5000/api/upload \
  -F "file=@document.pdf"
```

#### Search for documents
```bash
curl -X POST http://localhost:5000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "machine learning", "top_n": 5}'
```

## Use Cases

### 1. Research Paper Management
Upload academic papers and find related research:
```
1. Upload papers on various topics
2. When reading a new paper, upload it to find similar research
3. Cross-reference with existing knowledge base
```

### 2. Legal Document Analysis
Manage legal documents and find relevant precedents:
```
1. Build a database of legal documents
2. Upload new cases to find similar precedents
3. Extract relevant information from matched documents
```

### 3. Technical Documentation
Organize technical documentation and specifications:
```
1. Upload technical manuals and specifications
2. Search by keywords to find relevant sections
3. Find related documentation across different products
```

### 4. Content Management
Manage large collections of reports and articles:
```
1. Upload reports, articles, and documents
2. Automatically categorize by content similarity
3. Discover thematic connections between documents
```

## Advanced Features

### Keyword Extraction
- Automatic extraction of up to 50 top keywords per document
- Stop words and common words are filtered out
- Uses frequency analysis for relevance

### ML-Based Matching
- Uses TF-IDF (Term Frequency-Inverse Document Frequency) vectorization
- Cosine similarity for document comparison
- Supports both unigrams and bigrams for better context

### Database Features
- Fast keyword-based search using indexed database
- Metadata storage for efficient querying
- Document versioning through upload date tracking

## Tips and Best Practices

### For Best Search Results
1. **Use descriptive keywords**: More specific terms yield better matches
2. **Upload complete documents**: More content = better keyword extraction
3. **Regular updates**: Keep your database current for relevant results

### Performance Optimization
1. **Document count**: System works best with 100-10,000 documents
2. **File size**: Keep PDFs under 50MB for faster processing
3. **Page count**: Documents with 5-100 pages work best

### Maintenance
1. **Regular cleanup**: Remove outdated or duplicate documents
2. **Database backup**: Regularly backup `pdfstream.db`
3. **Upload folder**: Clean `uploads/` folder periodically if needed

## Troubleshooting

### PDF Not Processing
- **Issue**: PDF upload fails or no text extracted
- **Solution**: Ensure PDF is not scanned/image-only; use OCR-processed PDFs

### No Search Results
- **Issue**: Search returns no results
- **Solution**: Upload more documents; use broader search terms

### Slow Performance
- **Issue**: System runs slowly with many documents
- **Solution**: Consider database indexing; limit search results with `top_n`

### Server Won't Start
- **Issue**: Flask application fails to start
- **Solution**: Check if port 5000 is available; install all dependencies

## Configuration

Edit `config.py` to customize:
- Upload folder location
- Maximum file size
- Number of keywords to extract
- Server port and host

Environment variables:
```bash
export SECRET_KEY="your-secret-key"
export UPLOAD_FOLDER="/path/to/uploads"
export DATABASE_PATH="/path/to/database.db"
export PORT=5000
```

## System Requirements

### Minimum
- Python 3.8+
- 2GB RAM
- 1GB disk space

### Recommended
- Python 3.10+
- 4GB RAM
- 10GB disk space (for larger document collections)
- Modern web browser (Chrome, Firefox, Safari, Edge)

## Security Considerations

### For Production Use
1. Change the `SECRET_KEY` in production
2. Use HTTPS for secure communication
3. Implement authentication and authorization
4. Set file upload limits appropriately
5. Use a production WSGI server (gunicorn, uwsgi)

Example production command:
```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review API documentation
3. Open an issue on GitHub

## License

MIT License - See LICENSE file for details
