"""
PDFStream - Flask application
Main application file that provides REST API and web interface
"""

import os
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from database import DatabaseManager
from pdf_processor import PDFProcessor
from ml_matcher import MLMatcher

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
        
        # Process PDF
        processed_data = pdf_processor.process_pdf(filepath)
        
        # Save to database
        doc_id = db.add_document(
            filename=filename,
            filepath=filepath,
            file_size=processed_data['file_size'],
            page_count=processed_data['page_count'],
            text_content=processed_data['text'],
            keywords=processed_data['keywords']
        )
        
        # Refresh ML matcher
        refresh_ml_matcher()
        
        return jsonify({
            'success': True,
            'document_id': doc_id,
            'filename': filename,
            'page_count': processed_data['page_count'],
            'keywords_extracted': len(processed_data['keywords'])
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
    app.run(debug=True, host='0.0.0.0', port=5000)
