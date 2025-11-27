# PDFStream – Understand, Organise, and Explore PDF Documents

PDFStream is a self‑contained system that lets you build a searchable library of PDFs (e.g., research papers, reports, manuals) and discover related documents quickly. This README explains not only how to run the software but also why each component exists—using plain, non‑technical language where possible.

---
<!-- ## 1. What Problem Does PDFStream Solve?
When you accumulate many PDF documents, two challenges appear:
1. You cannot remember which document covered which concept.
2. Searching by filenames is unreliable because filenames rarely capture content.

PDFStream ingests each PDF, pulls out readable text, extracts meaningful keywords (either the authors’ own or automatically generated), and builds a “similarity map” so you can ask: “Which existing documents are most like this new one?” or “Show me papers about coordination in multi‑agent systems.” -->

---
## 1. Key Features
- Upload single PDFs or large batches (up to 500 at once).
- Automatically extract text—even from multi‑page documents.
- Detect author‑provided keyword sections ("Keywords:").
- Generate advanced keywords when authors do not supply them (using statistics + language patterns).
- Search by free text OR request documents similar to a specific document.
- Perform quick approximate keyword matching.
- View aggregated keywords by PI (Principal Investigator) name.
- Manually edit a document’s keyword list.
- Reprocess keywords in bulk if you add many new documents later.
- View aggregate statistics (counts, averages, latest upload date).
- Check that the system is healthy with a simple endpoint.

### 1.1 Advanced Feature Summary
| Feature | What It Does | Why It Matters |
|---------|--------------|----------------|
| Explicit Keyword Detection | Detects author-provided "Keywords:" blocks | Preserves human intent and domain wording |
| Advanced Keyword Extraction | Uses TF‑IDF, phrases, collocations, lemmatisation | Produces richer thematic descriptors |
| Simple Frequency Fallback | Counts frequent non‑stop words | Guarantees keywords even if text is difficult |
| Approximate Keyword Search | Matches keyword substrings case-insensitively | Quick filtering without full ML similarity |
| Batch Upload | Processes many PDFs sequentially (up to 500) | High-volume ingestion |
| Reprocess Keywords | Refreshes machine-derived keywords after growth | Raises quality as corpus evolves |
| Similarity Search | Finds thematically related documents | Accelerates literature/precedent discovery |
| Manual Keyword Editing | Lets user curate keyword list | Human refinement of machine suggestions |
| Keywords by PI | Aggregates keywords across all docs for a given PI | Quickly see a PI’s thematic footprint |
| Stats Endpoint | Aggregates counts & averages | Operational visibility |

---
## 2. How the System Works

### 2.1 Database (SQLite)
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
| pi_name | Optional PI/author name captured per document. |
| application_number | Optional application/record number captured per document. |

Because everything lives in a single file, backup is as easy as copying `pdfstream.db`.

#### Database Design & Indexing Rationale
| Aspect | Rationale |
|--------|-----------|
| Single SQLite file | Portable; atomic backup by copying one file; zero external service setup. |
| Separate `document_keywords` table | Normalises keywords for search; avoids scanning large JSON blobs for filtering; supports frequency metadata. |
| JSON `keywords` column in `documents` | Fast retrieval for display without joins; preserves original casing & ordering. |
| Lowercased index keywords | Enables case‑insensitive comparison while keeping human‑readable original variants in JSON. |
| `idx_keywords` index | Speeds exact matches and prefix LIKE (e.g. `keyword LIKE 'coord%'`). Full `%token%` patterns still require scan; future enhancement could add FTS5 or trigram indexing. |
| Explicit DELETE + ON DELETE CASCADE | Table declares cascade for safety, but code explicitly deletes keyword rows for clarity, deterministic row counts, and backward compatibility with older schema migrations. |
| In‑memory TF‑IDF similarity | Avoids adding full‑text module; keeps footprint minimal; recomputed vectoriser after corpus changes. |
| Approximate substring search | Simple LIKE approach keeps logic transparent; prepared statements mitigate injection; upgrade path: FTS5 or external search engine for large corpora. |
| Potential future improvements | Add FTS5 virtual table, store embeddings for semantic search, introduce incremental indexing for >10k documents. |

Security & Integrity Notes:
- All parameter substitution uses SQLite placeholders (`?`) to avoid SQL injection.
- Deleting a document first clears keyword index entries explicitly then removes the document row, ensuring no orphaned search artefacts remain.
- Large text fields are kept in the `documents` table to simplify backup; if size grows excessively consider moving raw text to a separate table or enabling compression.

### 2.2 Backend (Flask)
The backend:
1. Accepts uploads, validates they are PDFs, and stores them.
2. Calls the processing pipeline to extract text and keywords.
3. Updates the similarity model each time documents change.
4. Serves API responses to the web interface or external scripts.

### 2.3 Frontend (HTML / CSS / JavaScript)
The provided web page:
- Drag and drop PDFs to upload.
- View all stored documents quickly (without loading full text).
- Run searches and examine similarity scores.
- Open original PDFs in a browser tab.
- Edit keywords in a modal dialog.

### 2.4 Keyword Extraction Logic
Keywords are the short list of terms or phrases that summarise content. We use a priority chain:
1. **Explicit:** If the PDF includes a “Keywords:” block, we store those.
2. **Advanced:** If no explicit list exists, we analyse term importance (TF‑IDF), noun phrases, and multi‑word expressions (collocations). We also lemmatise (reduce words to base forms) to group variations (e.g., “coordinates,” “coordination”).
3. **Extracted:** Only if advanced methods fail, we fall back to simple word frequency filtering while excluding very common words.

### 2.5 ML Similarity (TF‑IDF + Cosine Similarity)
- **TF‑IDF (Term Frequency–Inverse Document Frequency):** Measures how important a word is to a specific document compared to the entire collection.
- **Cosine Similarity:** A mathematical way to compute how close two documents’ term profiles are. A higher number (closer to 1) means more similar content.

When you upload a new document, the system re‑calculates a shared representation so future searches include the latest additions.

---
## 3. Installation (Getting Started)
Choose either the quick script or manual steps.

### Option A: Startup Script (Recommended)
```bash
cd PDFStream
./start.sh
```
This script creates a virtual environment, installs dependencies, downloads language data (NLTK corpora), and starts the server.

### Option B: Manual
```bash
cd PDFStream
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open: `http://localhost:5000`

---
## 4. Use Workflow
1. Upload PDFs (single or batch).
2. Browse documents; spot duplicates or outdated items.
3. Use text search to find related materials.
4. If a document lacks clear keywords, edit them manually.
5. After a large import, run keyword reprocessing for better phrase coverage.
6. Periodically check `/api/stats` and back up `pdfstream.db`.

### Common Real-World Use Cases
1. **Research Paper Management** – Upload papers across topics; when reading a new one, upload it to surface related prior work.
2. **Legal Document Analysis** – Store case documents; find precedents by similarity or keyword, accelerating review.
3. **Technical Documentation** – Centralise product specifications; search for protocols or components quickly.
4. **Content & Report Collections** – Discover thematic clusters inside large sets of internal reports.

### Web Interface Actions
1. Drag & drop a PDF or click the upload area.
2. Observe status messages while processing occurs.
3. See document appear in the list (summary only, not full text).
4. Click a document to trigger similarity search (if implemented in UI) or view details.
5. Use the Keywords by PI section to see a PI’s aggregated keywords; use approximate keyword match to filter by terms.
6. Open a PDF in a new browser tab via its link.
7. Edit keywords in the modal when human-curated adjustments are desired.

---
## 5. API Overview
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
| Aggregated keywords by PI | `POST /api/keywords_by_pi` | Body with `pi_name` (or `query`) and optional `limit` |
| Replace keyword list | `PATCH /api/document/<id>/keywords` | Accepts list or CSV string |
| Advanced keyword reprocessing | `POST /api/reprocess_keywords` | Optional `{ "limit": N }` |
| Delete document | `DELETE /api/document/<id>` | Removes file + record |

For detailed request/response examples see `API.md`.

---
## 6. Practical Examples

### 6.1 Upload a PDF (Single)
```bash
curl -X POST http://localhost:5000/api/upload \
	-F "file=@paper.pdf"
```

Underlying SQL (simplified):
```sql
-- Insert document metadata & extracted content
INSERT INTO documents (
	filename, filepath, upload_date, file_size, page_count,
	text_content, keywords, created_at, keywords_source
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);

-- For each keyword (lowercased for indexing)
INSERT INTO document_keywords (document_id, keyword, frequency)
VALUES (?, ?, ?);
```

### 6.2 Batch Upload
```bash
curl -X POST http://localhost:5000/api/upload_batch \
	-F "files=@paper1.pdf" -F "files=@paper2.pdf"
```

Underlying SQL (per successful file):
```sql
INSERT INTO documents (
	filename, filepath, upload_date, file_size, page_count,
	text_content, keywords, created_at, keywords_source
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);

INSERT INTO document_keywords (document_id, keyword, frequency)
VALUES (?, ?, ?);  -- repeated for each keyword
```

### 6.3 Text Search
```bash
curl -X POST http://localhost:5000/api/search \
	-H "Content-Type: application/json" \
	-d '{"query": "multi agent coordination", "top_n": 5}'
```

Underlying SQL (corpus retrieval for similarity model):
```sql
-- Fetch document texts & IDs to build / refresh TF-IDF matrix
SELECT id, text_content FROM documents
WHERE text_content IS NOT NULL AND LENGTH(text_content) > 0;
```

Note: Similarity ranking is computed in memory (TF‑IDF + cosine); not via SQL ORDER BY.

### 6.4 Similar-To Search
```bash
curl -X POST http://localhost:5000/api/search \
	-H "Content-Type: application/json" \
	-d '{"document_id": 7, "top_n": 5}'
```

Underlying SQL (target + corpus retrieval):
```sql
-- Target document
SELECT id, text_content FROM documents WHERE id = ?;

-- Full corpus for similarity comparison
SELECT id, text_content FROM documents
WHERE text_content IS NOT NULL AND LENGTH(text_content) > 0;
```

### 6.5 Update Keywords
```bash
curl -X PATCH http://localhost:5000/api/document/7/keywords \
	-H "Content-Type: application/json" \
	-d '{"keywords": "game theory, negotiation, multi-agent"}'
```

Underlying SQL:
```sql
-- Ensure document exists
SELECT id FROM documents WHERE id = ?;

-- Replace JSON keyword list
UPDATE documents SET keywords = ? WHERE id = ?;

-- Clear old keyword index entries
DELETE FROM document_keywords WHERE document_id = ?;

-- Insert new indexed keywords (lowercased)
INSERT INTO document_keywords (document_id, keyword, frequency)
VALUES (?, ?, ?);  -- repeated
```

### 6.6 Reprocess Keywords
```bash
curl -X POST http://localhost:5000/api/reprocess_keywords \
	-H "Content-Type: application/json" \
	-d '{"limit": 10}'
```

Underlying SQL (selection + update sequence):
```sql
-- Select candidates (those not explicitly provided)
SELECT id, text_content FROM documents
WHERE keywords_source != 'explicit'
LIMIT ?;  -- optional limit

-- For each processed document
UPDATE documents SET keywords = ?, keywords_source = ? WHERE id = ?;

-- Refresh keyword index
DELETE FROM document_keywords WHERE document_id = ?;
INSERT INTO document_keywords (document_id, keyword, frequency)
VALUES (?, ?, ?);  -- repeated
```

### 6.7 Stats
```bash
curl http://localhost:5000/api/stats
```

Underlying SQL:
```sql
SELECT
	COUNT(*)                AS total_documents,
	AVG(file_size)          AS average_file_size,
	AVG(page_count)         AS average_page_count,
	MAX(upload_date)        AS last_upload_date
FROM documents;
```

### 6.8 Delete Document
```bash
curl -X DELETE http://localhost:5000/api/document/7
```

Underlying SQL:
```sql
-- Remove keyword index entries (explicit even with ON DELETE CASCADE)
DELETE FROM document_keywords WHERE document_id = ?;

-- Remove the document record
DELETE FROM documents WHERE id = ?;
```
Cascade Behaviour: The `document_keywords` table references `documents(id)` with `ON DELETE CASCADE`. The explicit DELETE is retained for clarity and accurate affected row accounting; if the schema evolves (e.g. extra dependent tables) the intention remains obvious.

### 6.9 Approximate Keyword Search
```bash
curl -X POST http://localhost:5000/api/search_keyword \
  -H "Content-Type: application/json" \
  -d '{"query": "coordination agent distributed"}'
```

Underlying SQL (dynamic LIKE pattern generation):
```sql
-- Tokens extracted from raw query (e.g. coordination, agent, distributed)
SELECT d.id, d.filename, d.filepath, d.upload_date, d.file_size,
       d.page_count, d.text_content, d.keywords, d.created_at,
       COUNT(DISTINCT dk.keyword) AS match_count
FROM documents d
JOIN document_keywords dk ON d.id = dk.document_id
WHERE dk.keyword LIKE '%coordination%' OR dk.keyword LIKE '%agent%' OR dk.keyword LIKE '%distributed%'
GROUP BY d.id
ORDER BY match_count DESC, d.created_at DESC
LIMIT ?;
```

The actual query is built at runtime based on cleaned tokens; parameters are bound safely with placeholders to avoid injection.
Tokenisation & Performance: Raw query text is split on non‑alphanumeric boundaries; very short tokens are ignored (<2 chars) to reduce noise. The resulting OR chain of LIKE clauses is acceptable for small/medium corpora; for very large sets consider adding a full‑text index (FTS5) or a separate search service. Input is never concatenated directly—placeholders ensure safe binding.

### 6.10 Aggregated Keywords by PI
```bash
curl -X POST http://localhost:5000/api/keywords_by_pi \
	-H "Content-Type: application/json" \
	-d '{"pi_name": "Dr Smith", "limit": 50}'
```

Example response (truncated):
```json
{
	"success": true,
	"pi_query": "Dr Smith",
	"count": 23,
	"keywords": [
		{"keyword": "machine learning", "total_frequency": 7},
		{"keyword": "classification", "total_frequency": 5}
	]
}
```

Underlying SQL (aggregating keyword frequencies across matching PI documents):
```sql
SELECT dk.keyword, SUM(dk.frequency) AS total_freq
FROM documents d
JOIN document_keywords dk ON dk.document_id = d.id
WHERE LOWER(COALESCE(d.pi_name, '')) LIKE ?
GROUP BY dk.keyword
ORDER BY total_freq DESC
LIMIT ?;  -- optional
```
Notes:
- Matching is case‑insensitive and uses substring `LIKE` on `pi_name` (e.g., `%smith%`).
- Returns frequency summed across all of the PI’s documents in the library.

---
## 7. Understanding Results
- **similarity_score**: A number like `0.82` means “82% similar” conceptually.
- **keywords_source**:
	- `explicit`: Human-written list found in the PDF.
	- `advanced`: Machine‑generated using linguistic/statistical analysis.
	- `extracted`: Simple frequency fallback.
- **keywords_extracted**: Count of keywords stored for that document.


---
## 8. Performance & Limits
- Maximum single file size: 700MB  (can increase).
- Maximum files per batch: 500 (can increase).
- Large scanned/image-only PDFs contain little extractable text; similarity and keywords may be sparse.


---
## 9. Maintenance Tips
| Task | Why |
|------|-----|
| Backup `pdfstream.db` weekly | Preserve your library if the machine fails. |
| Remove obsolete PDFs | Improves search relevance. |
| Reprocess keywords occasionally | Captures new phrase patterns as corpus evolves. |
| Monitor stats | Detect unusual growth or missing uploads. |

### Configuration & Environment Variables
You can customize deployment via `config.py` or environment variables:
| Variable | Purpose | Example |
|----------|---------|---------|
| `SECRET_KEY` | Flask session security (change in production) | `export SECRET_KEY="change_me"` |
| `UPLOAD_FOLDER` | Where PDFs are stored | `export UPLOAD_FOLDER="/data/pdfs"` |
| `DATABASE_PATH` | SQLite file location | `export DATABASE_PATH="/data/pdfstream.db"` |
| `PORT` | Server port | `export PORT=5000` |
| `HOST` | Bind host (default 0.0.0.0) | `export HOST=0.0.0.0` |

### System Requirements
| Level | Spec |
|-------|------|
| Minimum | Python 3.8+, 2GB RAM, 1GB disk |
| Recommended | Python 3.10+, 4GB RAM, 10GB disk (growing corpus) |

### Security Considerations (Production)
1. Set a strong `SECRET_KEY`.
2. Serve behind HTTPS (reverse proxy like Nginx + certs).
3. Add authentication/authorization for sensitive collections.
4. Adjust file size limits to match operational needs.
5. Use a production WSGI server (e.g., `gunicorn`, `uwsgi`).

Example production start:
```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

---
## 10. Extending the System
- Integrate OCR for scanned images.
- Add tagging or categorisation fields beyond keywords.
- Implement pagination for large document lists.
- Provide export of keyword summaries to CSV.
- Personalisation? 

---
## 11. Technology Summary
| Aspect | Choice | Reason |
|--------|--------|--------|
| Database | SQLite | Zero configuration, single-file backups. |
| Server | Flask | Simple, readable routing for a modest API. |
| ML | Scikit-learn TF‑IDF + cosine | Proven text similarity method with good accuracy for thematic grouping. |
| NLP | NLTK | Mature library for tokenisation, POS tagging, lemmatisation. |
| PDF Parsing | PyPDF2 | Widely used, supports text extraction for text-based PDFs. |
| Frontend | Vanilla HTML/CSS/JS | Lightweight, easy to modify. |

---
## 12. Troubleshooting Guide
| Symptom | Possible Cause | Action |
|---------|----------------|-------|
| Upload says “Not a PDF file” | Wrong extension or corrupted file | Confirm `.pdf` and re-download source. |
| Very few keywords extracted | PDF mostly images or poor text layer | Use OCR tool to convert before uploading. |
| Similarity seems low for all | Small corpus → weak differentiation | Upload more documents; reprocess keywords. |
| Server won’t start | Port 5000 in use | Stop other service or change port with env var. |
| Slow batch upload | Extremely large PDFs | Split batch or remove oversized files. |
| No search results | Too few documents or overly narrow query | Broaden query or upload more documents. |
| PDF not processing | Scanned/image-only (no text layer) | OCR the PDF before upload. |

---

### Support & Help
1. Review this README and `API.md` examples.
2. Check troubleshooting table.
3. Open a GitHub issue for unresolved problems.

---
## 13. Quick Reference Commands
```bash
# Start (script)
./start.sh

# Start (manual)
python app.py

# Backup database
cp pdfstream.db pdfstream_backup_$(date +%Y%m%d).db
```

---

