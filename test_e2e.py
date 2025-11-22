#!/usr/bin/env python3
"""
End-to-end test for PDFStream application
Tests the complete workflow: upload, process, search, and match documents
"""

import os
import sys
from database import DatabaseManager
from pdf_processor import PDFProcessor
from ml_matcher import MLMatcher

def main():
    print("=" * 70)
    print("PDFStream End-to-End Test")
    print("=" * 70 + "\n")
    
    # Initialize components
    print("1. Initializing components...")
    db = DatabaseManager("test_e2e.db")
    processor = PDFProcessor()
    matcher = MLMatcher()
    print("✓ Components initialized\n")
    
    # Test PDFs
    test_pdfs = [
        '/tmp/sample_pdfs/ml_document.pdf',
        '/tmp/sample_pdfs/python_document.pdf',
        '/tmp/sample_pdfs/data_science.pdf'
    ]
    
    # Upload and process PDFs
    print("2. Processing PDF documents...")
    doc_ids = []
    for pdf_path in test_pdfs:
        if not os.path.exists(pdf_path):
            print(f"   ⚠ Warning: {pdf_path} not found, skipping...")
            continue
        
        print(f"   Processing {os.path.basename(pdf_path)}...")
        
        # Process PDF
        result = processor.process_pdf(pdf_path)
        
        # Save to database
        doc_id = db.add_document(
            filename=result['filename'],
            filepath=result['filepath'],
            file_size=result['file_size'],
            page_count=result['page_count'],
            text_content=result['text'],
            keywords=result['keywords']
        )
        
        doc_ids.append(doc_id)
        print(f"   ✓ Uploaded: {result['filename']}")
        print(f"     - Pages: {result['page_count']}")
        print(f"     - Keywords: {len(result['keywords'])}")
        print(f"     - Top keywords: {', '.join(result['keywords'][:5])}")
    
    print(f"\n✓ Processed {len(doc_ids)} documents\n")
    
    # Train ML matcher
    print("3. Training ML matcher...")
    all_docs = db.get_all_documents()
    matcher.fit_documents(all_docs)
    print(f"✓ Trained on {len(all_docs)} documents\n")
    
    # Test search by query
    print("4. Testing search by query...")
    test_queries = [
        "machine learning and artificial intelligence",
        "python programming language",
        "data analysis and statistics"
    ]
    
    for query in test_queries:
        print(f"\n   Query: '{query}'")
        results = matcher.find_similar_documents(query, top_n=3)
        
        if results:
            print(f"   Found {len(results)} matching documents:")
            for doc_id, score in results:
                doc = db.get_document(doc_id)
                print(f"     - {doc['filename']}: {score*100:.1f}% match")
        else:
            print("   No matches found")
    
    print("\n✓ Search queries completed\n")
    
    # Test find similar documents
    if doc_ids:
        print("5. Testing similar document matching...")
        base_doc = db.get_document(doc_ids[0])
        print(f"   Finding documents similar to: {base_doc['filename']}")
        
        similar = matcher.find_similar_to_document(doc_ids[0], top_n=2)
        if similar:
            print(f"   Found {len(similar)} similar documents:")
            for doc_id, score in similar:
                doc = db.get_document(doc_id)
                print(f"     - {doc['filename']}: {score*100:.1f}% similar")
        else:
            print("   No similar documents found")
        
        print("\n✓ Similar document matching completed\n")
    
    # Display statistics
    print("6. System statistics:")
    print(f"   Total documents: {db.get_document_count()}")
    
    # Display all documents
    print("\n7. Document library:")
    all_docs = db.get_all_documents()
    for doc in all_docs:
        print(f"   - [{doc['id']}] {doc['filename']}")
        print(f"     Pages: {doc['page_count']}, Keywords: {len(doc['keywords'])}")
    
    # Clean up
    print("\n8. Cleaning up test database...")
    for doc_id in doc_ids:
        db.delete_document(doc_id)
    os.remove("test_e2e.db")
    print("✓ Cleanup completed\n")
    
    print("=" * 70)
    print("✓ End-to-end test completed successfully!")
    print("=" * 70)
    
    return 0

if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
