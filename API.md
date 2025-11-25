# PDFStream API Documentation

This document explains every available API endpoint, why it exists, and how to use it. We can think of the system as three layers working together:

1. Storage (Database) – remembers each PDF's text, size, pages, and extracted keywords so you do not have to re‑process files every time.
2. Processing (Backend & ML) – extracts readable text from PDFs, identifies meaningful keywords, and calculates how similar documents are to a query or to each other.
3. Presentation (Frontend / API) – provides simple web pages and REST endpoints so humans and other programs can interact with the collection.

## Base URL
All API endpoints (except the web interface `/`) live under:
```
http://localhost:5000/api
```

## General Conventions
- Success responses always include `"success": true`.
- Errors always include `"success": false` and an `"error"` message.
- Time fields use ISO‑8601 (e.g., `2024-01-15T10:30:00`).
- Similarity scores are numbers between 0 and 1; multiply by 100 to get a percentage.
- File size is in bytes.

## Endpoint Summary
| Purpose | Method & Path |
|---------|---------------|
| Health check (service up?) | GET `/api/health` |
| System statistics | GET `/api/stats` |
| List documents | GET `/api/documents` |
| Get single document | GET `/api/document/<id>` |
| Serve original PDF | GET `/pdf/<id>` (non‑API path) |
| Upload one PDF | POST `/api/upload` |
| Upload many PDFs | POST `/api/upload_batch` |
| Search by text or document | POST `/api/search` |
| Approximate keyword search | POST `/api/search_keyword` |
| Update (replace) keywords manually | PATCH `/api/document/<id>/keywords` |
| Reprocess keywords (advanced) | POST `/api/reprocess_keywords` |
| Delete a document | DELETE `/api/document/<id>` |

---
### 1. Health Check
Confirms the application is running (useful for monitoring).

**Endpoint:** `GET /api/health`
```json
{"success": true, "status": "ok"}
```

---
### 2. System Statistics
Provides simple aggregate measures: total documents, average file size, average page count, and date of most recent upload.

**Endpoint:** `GET /api/stats`
**Response:**
```json
{
  "success": true,
  "stats": {
    "total_documents": 42,
    "average_file_size": 153820,
    "average_page_count": 11.57,
    "last_upload_date": "2025-11-24T18:42:10"
  }
}
```

---
### 3. List All Documents
Returns a summary list (without full text to keep responses small). Use `limit` to cap the number returned.

**Endpoint:** `GET /api/documents`
**Query Parameters:**
- `limit` (optional, integer)
**Response:**
```json
{
  "success": true,
  "count": 2,
  "documents": [
    {
      "id": 7,
      "filename": "research_paper.pdf",
      "upload_date": "2025-11-24T18:42:10",
      "file_size": 238721,
      "page_count": 14,
      "keywords": ["multi-agent systems", "coordination", "distributed"],
      "created_at": "2025-11-24T18:42:10",
      "keywords_source": "advanced"
    },
    {
      "id": 3,
      "filename": "ml_intro.pdf",
      "upload_date": "2025-11-22T09:12:05",
      "file_size": 102400,
      "page_count": 9,
      "keywords": ["learning", "classification", "model"],
      "created_at": "2025-11-22T09:12:05",
      "keywords_source": "explicit"
    }
  ]
}
```

---
### 4. Get Document Details
Returns every stored field for a single document, including the full extracted text. (Large texts make responses big; avoid requesting many in sequence.)

**Endpoint:** `GET /api/document/<id>`
**Response:**
```json
{
  "success": true,
  "document": {
    "id": 7,
    "filename": "research_paper.pdf",
    "filepath": "uploads/research_paper.pdf",
    "upload_date": "2025-11-24T18:42:10",
    "file_size": 238721,
    "page_count": 14,
    "text_content": "Full extracted text...",
    "keywords": ["multi-agent systems", "coordination", "distributed"],
    "keywords_source": "advanced",
    "created_at": "2025-11-24T18:42:10"
  }
}
```

---
### 5. Serve Original PDF
Provides the raw PDF file for viewing in the browser. Not under `/api` intentionally so browsers can open it directly.

**Endpoint:** `GET /pdf/<id>`
**Response:** Binary PDF stream (no JSON). If the document or file is missing you receive a JSON error.

---
### 6. Upload One PDF
Adds a single PDF. The system checks the file extension and basic MIME type and then:
1. Extracts text page by page.
2. Looks for an author‑provided keyword block ("Keywords:").
3. If none found, performs advanced keyword extraction (TF‑IDF + phrases + collocations).
4. Falls back to simple frequency counting only if advanced extraction fails.
5. Stores everything and refreshes the similarity model.

**Endpoint:** `POST /api/upload`
**Content-Type:** `multipart/form-data`
**Form Field:** `file` (single PDF)
**Response:**
```json
{
  "success": true,
  "document_id": 7,
  "filename": "research_paper.pdf",
  "page_count": 14,
  "file_size": 238721,
  "keywords_extracted": 50,
  "keywords_source": "advanced",
  "keywords": ["multi-agent systems", "coordination", "distributed", "agent communication", "task allocation"],
  "explicit_keywords": []
}
```
**Notes:** Maximum file size is 700MB. Duplicate filenames are automatically de‑duplicated with numeric suffixes.

**cURL Example:**
```bash
curl -X POST http://localhost:5000/api/upload \
  -F "file=@/path/to/document.pdf"
```

---
### 7. Upload Many PDFs (Batch)
Processes up to 500 PDFs in a single request. Each file is handled sequentially; failures for one file do not stop others. Returns a per‑file result list and then re‑trains similarity.

**Endpoint:** `POST /api/upload_batch`
**Form Field:** `files` (multiple)
**Response (abridged):**
```json
{
  "success": true,
  "batch_count": 2,
  "results": [
    {"success": true, "document_id": 8, "filename": "paper1.pdf", "page_count": 12, "keywords_extracted": 40, "keywords_source": "advanced"},
    {"success": false, "filename": "notes.txt", "error": "Not a PDF file"}
  ]
}
```

**cURL Example:**
```bash
curl -X POST http://localhost:5000/api/upload_batch \
  -F "files=@paper1.pdf" -F "files=@paper2.pdf"
```

---
### 8. Search Documents (Text or Similar-To)
Two modes in the same endpoint:
1. Provide `query` text to find thematically similar documents.
2. Provide `document_id` to find documents similar to one already stored.
Uses TF‑IDF (term importance measure) and cosine similarity (mathematical measure of how close texts are).

**Endpoint:** `POST /api/search`
**Body (text search):**
```json
{"query": "multi agent coordination in robotics", "top_n": 5}
```
**Body (similar to document):**
```json
{"document_id": 7, "top_n": 5}
```
**Response:**
```json
{
  "success": true,
  "count": 2,
  "results": [
    {"id": 3, "filename": "ml_intro.pdf", "page_count": 9, "keywords": ["learning", "classification"], "similarity_score": 0.82},
    {"id": 1, "filename": "agents_review.pdf", "page_count": 20, "keywords": ["agent", "coordination"], "similarity_score": 0.74}
  ]
}
```

**cURL Example (Text):**
```bash
curl -X POST http://localhost:5000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "multi agent systems", "top_n": 5}'
```

**cURL Example (Similar-To):**
```bash
curl -X POST http://localhost:5000/api/search \
  -H "Content-Type: application/json" \
  -d '{"document_id": 7, "top_n": 5}'
```

---
### 9. Approximate Keyword Search
Useful for a quick filter: finds documents whose stored keywords contain any of the search tokens (substring match, case‑insensitive). Returns ranking by how many distinct keywords matched and recency.

**Endpoint:** `POST /api/search_keyword`
**Body:**
```json
{"query": "coordination agent"}
```
**Response (example):**
```json
{
  "success": true,
  "query": "coordination agent",
  "count": 1,
  "results": [
    {"id": 7, "filename": "research_paper.pdf", "keywords": ["multi-agent systems", "coordination", "distributed"], "matched_keywords": ["coordination", "multi-agent systems"], "match_count": 2}
  ]
}
```

---
### 10. Manually Update Keywords
Allows you to replace the keyword list (e.g., after human curation). System re‑fits similarity model so future searches reflect changes.

**Endpoint:** `PATCH /api/document/<id>/keywords`
**Body (list):**
```json
{"keywords": ["game theory", "negotiation", "multi-agent"]}
```
**Body (CSV alternative):**
```json
{"keywords": "game theory, negotiation, multi-agent"}
```
**Response:**
```json
{"success": true, "document_id": 7, "keywords": ["game theory", "negotiation", "multi-agent"], "count": 3}
```

---
### 11. Reprocess Keywords (Advanced Batch)
Re-runs advanced extraction for documents whose keywords were not explicitly provided by the author. Useful after adding many new documents to improve quality.

**Endpoint:** `POST /api/reprocess_keywords`
**Optional body:** `{ "limit": 20 }` to cap how many are processed.
**Response:**
```json
{
  "success": true,
  "processed": 12,
  "updated": [ {"document_id": 7, "count": 50}, {"document_id": 3, "count": 45} ]
}
```

---
### 12. Delete Document
Removes the database record and its stored PDF file. Similarity model is refreshed afterwards.

**Endpoint:** `DELETE /api/document/<id>`
**Response:**
```json
{"success": true, "message": "Document deleted successfully"}
```

**cURL Example:**
```bash
curl -X DELETE http://localhost:5000/api/document/7
```

---
## Error Responses
Standard error format:
```json
{"success": false, "error": "Description of what went wrong"}
```
Typical status codes:
- 400 – Invalid or missing input.
- 404 – Document or resource not found.
- 500 – Unexpected server error.

---
## Python Client Example (Extended)
```python
import requests
BASE_URL = "http://localhost:5000/api"

def upload_document(path):
    with open(path, 'rb') as f:
        return requests.post(f"{BASE_URL}/upload", files={'file': f}).json()

def upload_batch(paths):
    files = [('files', open(p, 'rb')) for p in paths]
    try:
        return requests.post(f"{BASE_URL}/upload_batch", files=files).json()
    finally:
        for _, fh in files: fh.close()

def search_text(query, top_n=10):
    return requests.post(f"{BASE_URL}/search", json={'query': query, 'top_n': top_n}).json()

def search_similar(doc_id, top_n=10):
    return requests.post(f"{BASE_URL}/search", json={'document_id': doc_id, 'top_n': top_n}).json()

def keyword_search(raw):
    return requests.post(f"{BASE_URL}/search_keyword", json={'query': raw}).json()

def update_keywords(doc_id, kws):
    return requests.patch(f"{BASE_URL}/document/{doc_id}/keywords", json={'keywords': kws}).json()

def stats():
    return requests.get(f"{BASE_URL}/stats").json()

if __name__ == "__main__":
    r = upload_document("paper.pdf")
    print("Uploaded", r.get('document_id'))
    print(search_text("multi agent coordination"))
    print(stats())
```

---
## JavaScript Fetch Examples (Extended)
```javascript
const BASE_URL = 'http://localhost:5000/api';

async function upload(file) {
  const fd = new FormData();
  fd.append('file', file);
  const res = await fetch(`${BASE_URL}/upload`, { method: 'POST', body: fd });
  return res.json();
}

async function uploadBatch(fileList) {
  const fd = new FormData();
  fileList.forEach(f => fd.append('files', f));
  const res = await fetch(`${BASE_URL}/upload_batch`, { method: 'POST', body: fd });
  return res.json();
}

async function searchText(query, topN=10) {
  const res = await fetch(`${BASE_URL}/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, top_n: topN })
  });
  return res.json();
}

async function searchSimilar(docId, topN=10) {
  const res = await fetch(`${BASE_URL}/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ document_id: docId, top_n: topN })
  });
  return res.json();
}

async function keywordSearch(raw) {
  const res = await fetch(`${BASE_URL}/search_keyword`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: raw })
  });
  return res.json();
}
```

---
## How Similarity Works
Each document is converted into a numeric profile describing which words and short phrases it contains and how important they are. Importance is higher if a term appears frequently in one document but not in most others (TF‑IDF). When you search, your query becomes a temporary “mini‑document” and we measure how close its profile is to each stored document. The closeness is the similarity score.

## Keyword Extraction Logic
1. Explicit List – If authors wrote “Keywords:” we capture those lines directly.
2. Advanced Extraction – Uses statistical term importance, word form reduction (lemmatisation), phrase grouping, and collocation detection to propose multi‑word concepts.
3. Simple Frequency – Counts common words (excluding ignored words) when advanced methods fail.

Understanding this hierarchy helps interpret results: “explicit” means human‑chosen; “advanced” means machine‑derived with linguistic analysis; “extracted” means plain counting.

## Limits & Performance Notes
- Upload size limit: 700MB per file.
- Batch upload: up to 500 files at once.
- Extremely large PDFs may produce less accurate keywords if they contain many scanned (image) pages without embedded text.

## Backups
All information lives in a single SQLite file (default `pdfstream.db`). Back up this file periodically to preserve your library.

---
End of API Documentation.
