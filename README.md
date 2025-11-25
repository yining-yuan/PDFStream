# PDFStream – Understand, Organize, and Explore PDF Documents

PDFStream is a self‑contained system that lets you build a searchable library of PDFs (e.g., research papers, reports, manuals) and discover related documents quickly. This README explains not only how to run the software but also why each component exists—using plain, non‑technical language where possible.

---
## 1. What Problem Does PDFStream Solve?
When you accumulate many PDF documents, two challenges appear:
1. You cannot remember which document covered which concept.
2. Searching by filenames is unreliable because filenames rarely capture content.

PDFStream ingests each PDF, pulls out readable text, extracts meaningful keywords (either the authors’ own or automatically generated), and builds a “similarity map” so you can ask: “Which existing documents are most like this new one?” or “Show me papers about coordination in multi‑agent systems.”

---
## 2. Key Features (What You Can Do)
- Upload single PDFs or large batches (up to 500 at once).
- Automatically extract text—even from multi‑page documents.
- Detect author‑provided keyword sections ("Keywords:").
- Generate advanced keywords when authors do not supply them (using statistics + language patterns).
- Search by free text OR request documents similar to a specific document.
- Perform quick approximate keyword matching.
- Manually edit a document’s keyword list.
- Reprocess keywords in bulk if you add many new documents later.
- View aggregate statistics (counts, averages, latest upload date).
- Check that the system is healthy with a simple endpoint.

---
## 3. How the System Thinks (The Rationale)

### 3.1 Database (SQLite)
Instead of re‑reading and re‑processing PDFs every time you search, the system stores results once in a lightweight local database file (`pdfstream.db`). This file holds:
| Field | Meaning |
|-------|---------|
| filename | Original file name (deduplicated if necessary). |
| filepath | Where the PDF is stored locally. |
| upload_date | When it was added (used for sorting & stats). |
| file_size | Size in bytes (helps watch storage usage). |
| page_count | Pages in the document (quality/length indicator). |
| text_content | Extracted full text (for similarity computation). |
| keywords | List used for quick filtering & display. |
| keywords_source | `explicit`, `advanced`, or `extracted` (see below). |

Because everything lives in a single file, backup is as easy as copying `pdfstream.db`.

### 3.2 Backend (Flask)
The backend is the “air traffic controller.” It:
1. Accepts uploads, validates they are PDFs, and stores them.
2. Calls the processing pipeline to extract text and keywords.
3. Updates the similarity model each time documents change.
4. Serves API responses to the web interface or external scripts.

### 3.3 Frontend (HTML / CSS / JavaScript)
The provided web page lets you:
- Drag and drop PDFs to upload.
- View all stored documents quickly (without loading full text).
- Run searches and examine similarity scores.
- Open original PDFs in a browser tab.
- Edit keywords in a modal dialog.

### 3.4 Keyword Extraction Logic
Keywords are the short list of terms or phrases that summarize content. We use a priority chain:
1. **Explicit:** If the PDF includes a “Keywords:” block, we trust the authors and store those.
2. **Advanced:** If no explicit list exists, we analyze term importance (TF‑IDF), noun phrases, and multi‑word expressions (collocations). We also lemmatize (reduce words to base forms) to group variations (e.g., “coordinates,” “coordination”).
3. **Extracted:** Only if advanced methods fail, we fall back to simple word frequency filtering out very common words.

### 3.5 ML Similarity (TF‑IDF + Cosine Similarity)
- **TF‑IDF (Term Frequency–Inverse Document Frequency):** Measures how important a word is to a specific document compared to the entire collection.
- **Cosine Similarity:** A mathematical way to compute how close two documents’ term profiles are. A higher number (closer to 1) means more similar content.

When you upload a new document, the system re‑calculates a shared representation so future searches include the latest additions.

---
## 4. Installation (Getting Started)
Choose either the quick script or manual steps.

### Option A: Startup Script (Recommended)
```bash
git clone https://github.com/Yining0913/PDFStream.git
cd PDFStream
./start.sh
```
This script creates a virtual environment, installs dependencies, downloads language data (NLTK corpora), and starts the server.

### Option B: Manual
```bash
git clone https://github.com/Yining0913/PDFStream.git
cd PDFStream
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open: `http://localhost:5000`

---
## 5. Daily Use Workflow
1. Upload PDFs (single or batch).
2. Browse documents; spot duplicates or outdated items.
3. Use text search to find related materials.
4. If a document lacks clear keywords, edit them manually.
5. After a large import, run keyword reprocessing for better phrase coverage.
6. Periodically check `/api/stats` and back up `pdfstream.db`.

---
## 6. API Overview (Human-Friendly)
| Action | Endpoint | Notes |
|--------|----------|-------|
| Check system health | `GET /api/health` | Returns `{status: "ok"}` |
| See overall statistics | `GET /api/stats` | Includes averages and last upload date |
| List documents | `GET /api/documents` | Optional `?limit=` query |
| View full details | `GET /api/document/<id>` | Includes full text content |
| Download/open PDF | `GET /pdf/<id>` | Displays original file |
| Upload one PDF | `POST /api/upload` | Form field `file` |
| Upload multiple PDFs | `POST /api/upload_batch` | Form field `files` (repeat) |
| Search by text | `POST /api/search` | Body with `query` and `top_n` |
| Find similar to an existing document | `POST /api/search` | Body with `document_id` |
| Keyword substring search | `POST /api/search_keyword` | Body with `query` |
| Replace keyword list | `PATCH /api/document/<id>/keywords` | Accepts list or CSV string |
| Advanced keyword reprocessing | `POST /api/reprocess_keywords` | Optional `{ "limit": N }` |
| Delete document | `DELETE /api/document/<id>` | Removes file + record |

For detailed request/response examples see `API.md`.

---
## 7. Practical Examples

### 7.1 Upload a PDF (Single)
```bash
curl -X POST http://localhost:5000/api/upload \
	-F "file=@paper.pdf"
```

### 7.2 Batch Upload
```bash
curl -X POST http://localhost:5000/api/upload_batch \
	-F "files=@paper1.pdf" -F "files=@paper2.pdf"
```

### 7.3 Text Search
```bash
curl -X POST http://localhost:5000/api/search \
	-H "Content-Type: application/json" \
	-d '{"query": "multi agent coordination", "top_n": 5}'
```

### 7.4 Similar-To Search
```bash
curl -X POST http://localhost:5000/api/search \
	-H "Content-Type: application/json" \
	-d '{"document_id": 7, "top_n": 5}'
```

### 7.5 Update Keywords
```bash
curl -X PATCH http://localhost:5000/api/document/7/keywords \
	-H "Content-Type: application/json" \
	-d '{"keywords": "game theory, negotiation, multi-agent"}'
```

### 7.6 Reprocess Keywords (Advanced)
```bash
curl -X POST http://localhost:5000/api/reprocess_keywords \
	-H "Content-Type: application/json" \
	-d '{"limit": 10}'
```

### 7.7 Stats
```bash
curl http://localhost:5000/api/stats
```

---
## 8. Understanding Results
- **similarity_score**: A number like `0.82` means “82% similar” conceptually.
- **keywords_source**:
	- `explicit`: Human-written list found in the PDF.
	- `advanced`: Machine‑generated using linguistic/statistical analysis.
	- `extracted`: Simple frequency fallback.
- **keywords_extracted**: Count of keywords stored for that document.

Interpreting these fields helps you decide trust level. Explicit lists usually reflect authors’ intention; advanced ones may introduce nuanced phrases you hadn’t considered.

---
## 9. Performance & Limits
- Maximum single file size: 700MB.
- Maximum files per batch: 500.
- Large scanned/image-only PDFs contain little extractable text; similarity and keywords may be sparse.
- After heavy document churn (additions/deletions), searches may take slightly longer while the model updates, but this is automatic.

---
## 10. Maintenance Tips
| Task | Why |
|------|-----|
| Backup `pdfstream.db` weekly | Preserve your library if the machine fails. |
| Remove obsolete PDFs | Improves search relevance. |
| Reprocess keywords occasionally | Captures new phrase patterns as corpus evolves. |
| Monitor stats | Detect unusual growth or missing uploads. |

---
## 11. Extending the System (Future Ideas)
- Integrate OCR for scanned images.
- Add tagging or categorization fields beyond keywords.
- Implement pagination for large document lists.
- Provide export of keyword summaries to CSV.

---
## 12. Technology Summary
| Aspect | Choice | Reason |
|--------|--------|--------|
| Database | SQLite | Zero configuration, single-file backups. |
| Server | Flask | Simple, readable routing for a modest API. |
| ML | Scikit-learn TF‑IDF + cosine | Proven text similarity method with good accuracy for thematic grouping. |
| NLP | NLTK | Mature library for tokenization, POS tagging, lemmatization. |
| PDF Parsing | PyPDF2 | Widely used, supports text extraction for text-based PDFs. |
| Frontend | Vanilla HTML/CSS/JS | Lightweight, easy to modify. |

---
## 13. Troubleshooting Guide
| Symptom | Possible Cause | Action |
|---------|----------------|-------|
| Upload says “Not a PDF file” | Wrong extension or corrupted file | Confirm `.pdf` and re-download source. |
| Very few keywords extracted | PDF mostly images or poor text layer | Use OCR tool to convert before uploading. |
| Similarity seems low for all | Small corpus → weak differentiation | Upload more documents; reprocess keywords. |
| Server won’t start | Port 5000 in use | Stop other service or change port with env var. |
| Slow batch upload | Extremely large PDFs | Split batch or remove oversized files. |

---
## 14. Licensing
MIT License – You may use, modify, and distribute with attribution.

---
## 15. Quick Reference Commands
```bash
# Start (script)
./start.sh

# Start (manual)
python app.py

# Backup database
cp pdfstream.db pdfstream_backup_$(date +%Y%m%d).db
```

---
## 16. Final Notes
PDFStream’s value grows with the richness of its corpus. Upload a variety of documents, curate keywords where needed, and leverage advanced extraction to surface multi‑word concepts. Treat keywords as a living index—refine them to sharpen future discovery.

Enjoy exploring your document collection.
