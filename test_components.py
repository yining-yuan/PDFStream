#!/usr/bin/env python3
"""
Simple test script to verify PDFStream functionality
"""

import os
import sys
from database import DatabaseManager
from pdf_processor import PDFProcessor
from ml_matcher import MLMatcher

def test_database():
    """Test database operations"""
    print("Testing database...")
    
    # Create test database
    db = DatabaseManager("test_pdfstream.db")
    
    # Add a test document
    doc_id = db.add_document(
        filename="test.pdf",
        filepath="/tmp/test.pdf",
        file_size=1024,
        page_count=1,
        text_content="This is a test document about machine learning and artificial intelligence.",
        keywords=["machine", "learning", "artificial", "intelligence", "test"]
    )
    
    print(f"✓ Added document with ID: {doc_id}")
    
    # Retrieve document
    doc = db.get_document(doc_id)
    assert doc is not None
    assert doc['filename'] == "test.pdf"
    print(f"✓ Retrieved document: {doc['filename']}")
    
    # Get all documents
    docs = db.get_all_documents()
    assert len(docs) >= 1
    print(f"✓ Found {len(docs)} documents")
    
    # Search by keywords
    results = db.search_by_keywords(["machine", "learning"])
    assert len(results) >= 1
    print(f"✓ Keyword search returned {len(results)} results")
    
    # Clean up
    db.delete_document(doc_id)
    os.remove("test_pdfstream.db")
    
    print("✓ Database tests passed!\n")

def test_pdf_processor():
    """Test PDF processor"""
    print("Testing PDF processor...")
    
    processor = PDFProcessor()
    
    # Test keyword extraction
    text = "Machine learning is a subset of artificial intelligence. Deep learning is a subset of machine learning."
    keywords = processor.extract_keywords(text, top_n=10)
    
    assert len(keywords) > 0
    assert "machine" in keywords or "learning" in keywords
    print(f"✓ Extracted {len(keywords)} keywords")
    print(f"  Top keywords: {keywords[:5]}")
    
    print("✓ PDF processor tests passed!\n")

def test_ml_matcher():
    """Test ML matcher"""
    print("Testing ML matcher...")
    
    matcher = MLMatcher()
    
    # Create test documents
    documents = [
        {'id': 1, 'text_content': 'Machine learning and artificial intelligence are transforming technology.'},
        {'id': 2, 'text_content': 'Deep learning neural networks are powerful tools for AI.'},
        {'id': 3, 'text_content': 'Python is a popular programming language for data science.'},
    ]
    
    # Fit documents
    matcher.fit_documents(documents)
    print(f"✓ Fitted {len(documents)} documents")
    
    # Find similar documents
    query = "artificial intelligence and machine learning"
    results = matcher.find_similar_documents(query, top_n=2)
    
    assert len(results) > 0
    print(f"✓ Found {len(results)} similar documents")
    print(f"  Top match: Document {results[0][0]} with score {results[0][1]:.3f}")
    
    # Find similar to document
    similar = matcher.find_similar_to_document(1, top_n=2)
    assert len(similar) > 0
    print(f"✓ Found {len(similar)} documents similar to document 1")
    
    print("✓ ML matcher tests passed!\n")

def main():
    """Run all tests"""
    print("=" * 60)
    print("PDFStream Component Tests")
    print("=" * 60 + "\n")
    
    try:
        test_database()
        test_pdf_processor()
        test_ml_matcher()
        
        print("=" * 60)
        print("✓ All tests passed successfully!")
        print("=" * 60)
        return 0
    
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
