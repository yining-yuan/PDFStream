# PDFStream API Documentation

## Overview
PDFStream provides a RESTful API for managing and searching PDF documents using ML-based thematic matching.

## Base URL
```
http://localhost:5000/api
```

## Endpoints

### 1. Get System Statistics
Get overall system statistics.

**Endpoint:** `GET /api/stats`

**Response:**
```json
{
  "success": true,
  "stats": {
    "total_documents": 10
  }
}
```

### 2. List All Documents
Get a list of all documents in the system.

**Endpoint:** `GET /api/documents`

**Query Parameters:**
- `limit` (optional): Maximum number of documents to return

**Response:**
```json
{
  "success": true,
  "count": 3,
  "documents": [
    {
      "id": 1,
      "filename": "document.pdf",
      "upload_date": "2024-01-15T10:30:00",
      "file_size": 102400,
      "page_count": 5,
      "keywords": ["keyword1", "keyword2", "..."],
      "created_at": "2024-01-15T10:30:00"
    }
  ]
}
```

### 3. Get Document Details
Get details of a specific document.

**Endpoint:** `GET /api/document/<id>`

**Response:**
```json
{
  "success": true,
  "document": {
    "id": 1,
    "filename": "document.pdf",
    "filepath": "/path/to/document.pdf",
    "upload_date": "2024-01-15T10:30:00",
    "file_size": 102400,
    "page_count": 5,
    "text_content": "Full text content...",
    "keywords": ["keyword1", "keyword2"],
    "created_at": "2024-01-15T10:30:00"
  }
}
```

### 4. Upload PDF Document
Upload and process a new PDF document.

**Endpoint:** `POST /api/upload`

**Content-Type:** `multipart/form-data`

**Form Data:**
- `file`: PDF file to upload

**Response:**
```json
{
  "success": true,
  "document_id": 5,
  "filename": "document.pdf",
  "page_count": 10,
  "keywords_extracted": 50
}
```

**cURL Example:**
```bash
curl -X POST http://localhost:5000/api/upload \
  -F "file=@/path/to/document.pdf"
```

### 5. Search Documents
Search for similar documents using text query or find documents similar to a specific document.

**Endpoint:** `POST /api/search`

**Content-Type:** `application/json`

**Request Body (Text Search):**
```json
{
  "query": "machine learning and artificial intelligence",
  "top_n": 10
}
```

**Request Body (Similar Documents):**
```json
{
  "document_id": 5,
  "top_n": 10
}
```

**Response:**
```json
{
  "success": true,
  "count": 3,
  "results": [
    {
      "id": 2,
      "filename": "ml_paper.pdf",
      "upload_date": "2024-01-15T10:30:00",
      "file_size": 204800,
      "page_count": 12,
      "keywords": ["machine", "learning", "neural"],
      "similarity_score": 0.85,
      "created_at": "2024-01-15T10:30:00"
    }
  ]
}
```

**cURL Example (Text Search):**
```bash
curl -X POST http://localhost:5000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "machine learning", "top_n": 5}'
```

**cURL Example (Similar Documents):**
```bash
curl -X POST http://localhost:5000/api/search \
  -H "Content-Type: application/json" \
  -d '{"document_id": 1, "top_n": 5}'
```

### 6. Delete Document
Delete a document from the system.

**Endpoint:** `DELETE /api/document/<id>`

**Response:**
```json
{
  "success": true,
  "message": "Document deleted successfully"
}
```

**cURL Example:**
```bash
curl -X DELETE http://localhost:5000/api/document/5
```

## Error Responses

All endpoints return error responses in the following format:

```json
{
  "success": false,
  "error": "Error description"
}
```

Common HTTP status codes:
- `200`: Success
- `400`: Bad request (invalid parameters)
- `404`: Resource not found
- `500`: Internal server error

## Python Client Example

```python
import requests

# Base URL
BASE_URL = "http://localhost:5000/api"

# Upload a document
def upload_document(file_path):
    with open(file_path, 'rb') as f:
        response = requests.post(
            f"{BASE_URL}/upload",
            files={'file': f}
        )
    return response.json()

# Search by text
def search_documents(query, top_n=10):
    response = requests.post(
        f"{BASE_URL}/search",
        json={'query': query, 'top_n': top_n}
    )
    return response.json()

# Find similar documents
def find_similar(document_id, top_n=10):
    response = requests.post(
        f"{BASE_URL}/search",
        json={'document_id': document_id, 'top_n': top_n}
    )
    return response.json()

# Get all documents
def get_all_documents():
    response = requests.get(f"{BASE_URL}/documents")
    return response.json()

# Example usage
if __name__ == "__main__":
    # Upload
    result = upload_document("document.pdf")
    print(f"Uploaded document {result['document_id']}")
    
    # Search
    results = search_documents("machine learning")
    for doc in results['results']:
        print(f"{doc['filename']}: {doc['similarity_score']:.2%}")
```

## JavaScript Client Example

```javascript
const BASE_URL = 'http://localhost:5000/api';

// Upload a document
async function uploadDocument(file) {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await fetch(`${BASE_URL}/upload`, {
    method: 'POST',
    body: formData
  });
  
  return await response.json();
}

// Search documents
async function searchDocuments(query, topN = 10) {
  const response = await fetch(`${BASE_URL}/search`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ query, top_n: topN })
  });
  
  return await response.json();
}

// Get all documents
async function getAllDocuments() {
  const response = await fetch(`${BASE_URL}/documents`);
  return await response.json();
}
```
