"""
PDFStream - Flask application
Main application file that provides REST API and web interface
"""

import os
import re
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from database import DatabaseManager
from pdf_processor import PDFProcessor
from ml_matcher import MLMatcher

# (request already imported above)
# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'dev-key-change-in-production'
if app.config['SECRET_KEY'] == 'dev-key-change-in-production' and not os.environ.get('FLASK_ENV') == 'development':
    import warnings
    warnings.warn("WARNING: Using default SECRET_KEY. Set SECRET_KEY environment variable for production!")
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
CORS(app)

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize components
db = DatabaseManager()
pdf_processor = PDFProcessor()
ml_matcher = MLMatcher()

# Initialize ML matcher with existing documents
def refresh_ml_matcher():
    """Refresh ML matcher with all documents from database"""
    documents = db.get_all_documents()
    ml_matcher.fit_documents(documents)

# Refresh matcher on startup
refresh_ml_matcher()


@app.route('/')
def index():
    """Serve the main web interface"""
    return render_template('index.html')


@app.route('/api/documents', methods=['GET'])
def get_documents():
    """Get all documents"""
    try:
        limit = request.args.get('limit', type=int)
        documents = db.get_all_documents(limit=limit)
        
        # Remove text content from list view for efficiency
        for doc in documents:
            doc.pop('text_content', None)
        
        return jsonify({
            'success': True,
            'documents': documents,
            'count': len(documents)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/document/<int:doc_id>', methods=['GET'])
def get_document(doc_id):
    """Get a specific document by ID"""
    try:
        document = db.get_document(doc_id)
        if document:
            return jsonify({'success': True, 'document': document})
        else:
            return jsonify({'success': False, 'error': 'Document not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/upload', methods=['POST'])
def upload_pdf():
    """Upload and process a PDF file"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'success': False, 'error': 'Only PDF files are allowed'}), 400
        
        # Save file
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Handle duplicate filenames (with a maximum of 1000 attempts)
        base, ext = os.path.splitext(filepath)
        counter = 1
        max_attempts = 1000
        while os.path.exists(filepath) and counter < max_attempts:
            filepath = f"{base}_{counter}{ext}"
            filename = os.path.basename(filepath)
            counter += 1
        
        if os.path.exists(filepath):
            return jsonify({'success': False, 'error': 'Too many files with the same name'}), 400
        
        file.save(filepath)
        
        # Gather existing corpus texts for advanced extraction (excluding empty)
        corpus_texts = [t for t in db.get_all_texts() if t and t.strip()]

        # Process PDF (pass corpus for advanced keyword extraction fallback)
        processed_data = pdf_processor.process_pdf(filepath, corpus_texts=corpus_texts)
        
        # Save to database
        doc_id = db.add_document(
            filename=filename,
            filepath=filepath,
            file_size=processed_data['file_size'],
            page_count=processed_data['page_count'],
            text_content=processed_data['text'],
            keywords=processed_data['keywords'],
            keywords_source=processed_data.get('keywords_source','extracted')
        )
        
        # Refresh ML matcher
        refresh_ml_matcher()
        
        return jsonify({
            'success': True,
            'document_id': doc_id,
            'filename': filename,
            'page_count': processed_data['page_count'],
            'keywords_extracted': len(processed_data['keywords']),
            'keywords': processed_data.get('keywords', []),
            'explicit_keywords': processed_data.get('keywords_source') == 'explicit' and processed_data.get('keywords', []) or [],
            'keywords_source': processed_data.get('keywords_source', 'extracted')
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/search', methods=['POST'])
def search_documents():
    """Search for similar documents"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        query_text = data.get('query', '')
        document_id = data.get('document_id')
        top_n = data.get('top_n', 10)
        
        results = []
        
        if document_id:
            # Find similar documents to a specific document
            similar_docs = ml_matcher.find_similar_to_document(document_id, top_n=top_n)
            
            for doc_id, score in similar_docs:
                doc = db.get_document(doc_id)
                if doc:
                    doc.pop('text_content', None)  # Remove text for efficiency
                    doc['similarity_score'] = score
                    results.append(doc)
        
        elif query_text:
            # Find similar documents based on query text
            similar_docs = ml_matcher.find_similar_documents(query_text, top_n=top_n)
            
            for doc_id, score in similar_docs:
                doc = db.get_document(doc_id)
                if doc:
                    doc.pop('text_content', None)
                    doc['similarity_score'] = score
                    results.append(doc)
        
        else:
            return jsonify({'success': False, 'error': 'No query or document_id provided'}), 400
        
        return jsonify({
            'success': True,
            'results': results,
            'count': len(results)
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/document/<int:doc_id>', methods=['DELETE'])
def delete_document(doc_id):
    """Delete a document"""
    try:
        # Get document info first
        document = db.get_document(doc_id)
        if not document:
            return jsonify({'success': False, 'error': 'Document not found'}), 404
        
        # Delete file from disk
        if os.path.exists(document['filepath']):
            os.remove(document['filepath'])
        
        # Delete from database
        db.delete_document(doc_id)
        
        # Refresh ML matcher
        refresh_ml_matcher()
        
        return jsonify({'success': True, 'message': 'Document deleted successfully'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/search_keyword', methods=['POST'])
def search_keyword():
    """Exact keyword search: returns documents containing the given keyword"""
    try:
        data = request.get_json() or {}
        keyword = (data.get('keyword') or '').strip().lower()
        if not keyword:
            return jsonify({'success': False, 'error': 'Keyword is required'}), 400

        # Perform keyword search (single keyword exact match)
        results = db.search_by_keywords([keyword], limit=100)

        # Strip large text content for list view
        for doc in results:
            if 'text_content' in doc:
                doc.pop('text_content')

        return jsonify({
            'success': True,
            'keyword': keyword,
            'results': results,
            'count': len(results)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/pdf/<int:doc_id>', methods=['GET'])
def serve_pdf(doc_id):
    """Serve the original PDF file in a new tab"""
    try:
        document = db.get_document(doc_id)
        if not document:
            return jsonify({'success': False, 'error': 'Document not found'}), 404

        filepath = document.get('filepath')
        if not filepath or not os.path.isfile(filepath):
            return jsonify({'success': False, 'error': 'File not found on disk'}), 404

        directory, filename = os.path.split(filepath)
        # Send file without forcing download so browser can display inline if supported
        return send_from_directory(directory, filename, as_attachment=False)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/document/<int:doc_id>/keywords', methods=['PATCH'])
def update_keywords(doc_id):
    """Manually amend keywords for a document"""
    try:
        data = request.get_json() or {}
        keywords = data.get('keywords')
        if not isinstance(keywords, list):
            # Allow also a CSV string
            if isinstance(keywords, str):
                keywords = [k.strip() for k in re.split(r'[;,]', keywords) if k.strip()]
            else:
                return jsonify({'success': False, 'error': 'keywords must be a list or CSV string'}), 400
        if len(keywords) == 0:
            return jsonify({'success': False, 'error': 'At least one keyword required'}), 400
        # Update
        updated = db.update_document_keywords(doc_id, keywords)
        if not updated:
            return jsonify({'success': False, 'error': 'Update failed (document may not exist)'}), 404
        doc = db.get_document(doc_id)
        # Do not refit ML matcher (text unchanged), but could refresh keyword-based caches if any.
        return jsonify({'success': True, 'document_id': doc_id, 'keywords': doc['keywords'], 'count': len(doc['keywords'])})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/reprocess_keywords', methods=['POST'])
def reprocess_keywords():
    """Batch reprocess keywords for documents that are not explicit using advanced extraction."""
    try:
        data = request.get_json() or {}
        limit = data.get('limit')  # optional cap
        documents = db.get_all_documents()
        corpus_texts = [d.get('text_content','') for d in documents if d.get('text_content')]
        updated = []
        processed_count = 0
        for doc in documents:
            if limit and processed_count >= limit:
                break
            src = (doc.get('keywords_source') or 'extracted').lower()
            if src == 'explicit':
                continue
            text = doc.get('text_content','')
            if not text:
                continue
            other_corpus = [t for t in corpus_texts if t != text]
            advanced_keywords = pdf_processor.extract_keywords_advanced(text, corpus_texts=other_corpus, top_n=50)
            if advanced_keywords:
                ok = db.update_document_keywords_with_source(doc['id'], advanced_keywords, 'advanced')
                if ok:
                    updated.append({'document_id': doc['id'], 'count': len(advanced_keywords)})
                    processed_count += 1
        return jsonify({'success': True, 'updated': updated, 'processed': processed_count})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/upload_batch', methods=['POST'])
def upload_batch():
    """Upload and process multiple PDF files in a single request.
    Sequential processing chosen for consistency with current corpus-based keyword extraction.
    Returns a list of per-file results.
    """
    try:
        if 'files' not in request.files:
            # Support files[] alternative naming
            file_list = [f for _, f in request.files.items()]
            if not file_list:
                return jsonify({'success': False, 'error': 'No files provided (use form field name "files" with multiple PDFs)'}), 400
        else:
            file_list = request.files.getlist('files')

        if not file_list:
            return jsonify({'success': False, 'error': 'Empty file list'}), 400

        # Limit number of files to prevent overload
        MAX_FILES = 15
        if len(file_list) > MAX_FILES:
            return jsonify({'success': False, 'error': f'Maximum {MAX_FILES} files allowed per batch'}), 400

        # Preload corpus texts once
        corpus_texts = [t for t in db.get_all_texts() if t and t.strip()]

        results = []
        for f in file_list:
            filename_orig = f.filename
            if not filename_orig or not filename_orig.lower().endswith('.pdf'):
                results.append({'filename': filename_orig or '', 'success': False, 'error': 'Not a PDF file'})
                continue
            filename = secure_filename(filename_orig)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            base, ext = os.path.splitext(filepath)
            counter = 1
            while os.path.exists(filepath) and counter < 1000:
                filepath = f"{base}_{counter}{ext}"
                filename = os.path.basename(filepath)
                counter += 1
            if os.path.exists(filepath):
                results.append({'filename': filename_orig, 'success': False, 'error': 'Too many duplicate filenames'})
                continue
            try:
                f.save(filepath)
            except Exception as save_err:
                results.append({'filename': filename_orig, 'success': False, 'error': f'Failed to save file: {save_err}'})
                continue
            try:
                processed = pdf_processor.process_pdf(filepath, corpus_texts=corpus_texts)
                doc_id = db.add_document(
                    filename=filename,
                    filepath=filepath,
                    file_size=processed['file_size'],
                    page_count=processed['page_count'],
                    text_content=processed['text'],
                    keywords=processed['keywords'],
                    keywords_source=processed.get('keywords_source', 'extracted')
                )
                results.append({
                    'success': True,
                    'document_id': doc_id,
                    'filename': filename,
                    'page_count': processed['page_count'],
                    'keywords_extracted': len(processed['keywords']),
                    'keywords_source': processed.get('keywords_source', 'extracted')
                })
            except Exception as proc_err:
                results.append({'filename': filename_orig, 'success': False, 'error': f'Processing failed: {proc_err}'})
                continue
        # Refresh ML matcher after batch
        refresh_ml_matcher()
        return jsonify({'success': True, 'batch_count': len(results), 'results': results})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get system statistics"""
    try:
        document_count = db.get_document_count()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_documents': document_count
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    print("Starting PDFStream application...")
    print("Access the web interface at http://localhost:5000")
    
    # Use debug mode only in development
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    if debug_mode:
        print("WARNING: Running in DEBUG mode - not suitable for production!")
    
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)
