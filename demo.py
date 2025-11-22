#!/usr/bin/env python3
"""
Example script demonstrating programmatic usage of PDFStream
"""

import requests
import json
import sys
import time

# Configuration
BASE_URL = "http://localhost:5000/api"

def print_section(title):
    """Print a section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")

def upload_document(file_path):
    """Upload a PDF document"""
    print(f"Uploading: {file_path}")
    try:
        with open(file_path, 'rb') as f:
            response = requests.post(
                f"{BASE_URL}/upload",
                files={'file': f}
            )
        
        if response.status_code == 200:
            result = response.json()
            if result['success']:
                print(f"✓ Uploaded successfully!")
                print(f"  Document ID: {result['document_id']}")
                print(f"  Pages: {result['page_count']}")
                print(f"  Keywords extracted: {result['keywords_extracted']}")
                return result['document_id']
            else:
                print(f"✗ Upload failed: {result.get('error', 'Unknown error')}")
        else:
            print(f"✗ HTTP Error: {response.status_code}")
    
    except FileNotFoundError:
        print(f"✗ File not found: {file_path}")
    except requests.RequestException as e:
        print(f"✗ Request failed: {e}")
    
    return None

def get_all_documents():
    """Get list of all documents"""
    try:
        response = requests.get(f"{BASE_URL}/documents")
        if response.status_code == 200:
            result = response.json()
            if result['success']:
                return result['documents']
    except requests.RequestException as e:
        print(f"✗ Request failed: {e}")
    
    return []

def search_by_text(query, top_n=5):
    """Search documents by text query"""
    print(f"Searching for: '{query}'")
    try:
        response = requests.post(
            f"{BASE_URL}/search",
            json={'query': query, 'top_n': top_n}
        )
        
        if response.status_code == 200:
            result = response.json()
            if result['success']:
                print(f"✓ Found {result['count']} matching documents:\n")
                for i, doc in enumerate(result['results'], 1):
                    score = doc['similarity_score'] * 100
                    print(f"  {i}. {doc['filename']}")
                    print(f"     Similarity: {score:.1f}%")
                    print(f"     Pages: {doc['page_count']}")
                    print(f"     Keywords: {', '.join(doc['keywords'][:5])}")
                    print()
                return result['results']
            else:
                print(f"✗ Search failed: {result.get('error', 'Unknown error')}")
        else:
            print(f"✗ HTTP Error: {response.status_code}")
    
    except requests.RequestException as e:
        print(f"✗ Request failed: {e}")
    
    return []

def find_similar_documents(document_id, top_n=5):
    """Find documents similar to a specific document"""
    print(f"Finding documents similar to document ID {document_id}")
    try:
        response = requests.post(
            f"{BASE_URL}/search",
            json={'document_id': document_id, 'top_n': top_n}
        )
        
        if response.status_code == 200:
            result = response.json()
            if result['success']:
                print(f"✓ Found {result['count']} similar documents:\n")
                for i, doc in enumerate(result['results'], 1):
                    score = doc['similarity_score'] * 100
                    print(f"  {i}. {doc['filename']}")
                    print(f"     Similarity: {score:.1f}%")
                    print(f"     Pages: {doc['page_count']}")
                    print()
                return result['results']
            else:
                print(f"✗ Search failed: {result.get('error', 'Unknown error')}")
        else:
            print(f"✗ HTTP Error: {response.status_code}")
    
    except requests.RequestException as e:
        print(f"✗ Request failed: {e}")
    
    return []

def get_statistics():
    """Get system statistics"""
    try:
        response = requests.get(f"{BASE_URL}/stats")
        if response.status_code == 200:
            result = response.json()
            if result['success']:
                return result['stats']
    except requests.RequestException as e:
        print(f"✗ Request failed: {e}")
    
    return {}

def main():
    """Main demo function"""
    print("\n" + "=" * 70)
    print("  PDFStream API Demo")
    print("=" * 70)
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/stats", timeout=2)
        if response.status_code != 200:
            print("\n✗ Error: PDFStream server is not responding correctly")
            print("  Please start the server with: python app.py")
            return 1
    except requests.RequestException:
        print("\n✗ Error: Cannot connect to PDFStream server")
        print("  Please start the server with: python app.py")
        return 1
    
    # Get initial statistics
    print_section("System Statistics")
    stats = get_statistics()
    print(f"Total documents in database: {stats.get('total_documents', 0)}")
    
    # List all documents
    print_section("Document Library")
    documents = get_all_documents()
    if documents:
        print(f"Found {len(documents)} documents:\n")
        for doc in documents:
            print(f"  [{doc['id']}] {doc['filename']}")
            print(f"      Pages: {doc['page_count']}, Size: {doc['file_size']/1024:.2f} KB")
            print(f"      Keywords: {', '.join(doc['keywords'][:5])}")
            print()
    else:
        print("No documents found in the database.")
        print("\nTip: Upload PDF files at /tmp/sample_pdfs/ to test the system")
    
    # Upload example (if sample PDFs exist)
    print_section("Upload Example")
    sample_files = [
        '/tmp/sample_pdfs/ml_document.pdf',
        '/tmp/sample_pdfs/python_document.pdf',
        '/tmp/sample_pdfs/data_science.pdf'
    ]
    
    uploaded_ids = []
    for file_path in sample_files:
        try:
            doc_id = upload_document(file_path)
            if doc_id:
                uploaded_ids.append(doc_id)
                time.sleep(0.5)  # Small delay between uploads
        except Exception as e:
            print(f"Skipping {file_path}: {e}")
    
    if not uploaded_ids:
        print("No sample PDFs found. Using existing documents for demo.")
        uploaded_ids = [doc['id'] for doc in documents[:1]]
    
    # Search examples
    if uploaded_ids or documents:
        print_section("Text Search Examples")
        
        search_queries = [
            "machine learning and artificial intelligence",
            "python programming",
            "data science"
        ]
        
        for query in search_queries:
            search_by_text(query, top_n=3)
            time.sleep(0.5)
        
        # Find similar documents
        if uploaded_ids:
            print_section("Similar Document Search")
            find_similar_documents(uploaded_ids[0], top_n=3)
    
    # Final statistics
    print_section("Final Statistics")
    stats = get_statistics()
    print(f"Total documents in database: {stats.get('total_documents', 0)}")
    
    print("\n" + "=" * 70)
    print("  Demo completed! Access the web UI at http://localhost:5000")
    print("=" * 70 + "\n")
    
    return 0

if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
