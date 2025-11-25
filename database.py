"""
Database module for PDFStream
Handles SQLite database operations for PDF metadata and keywords
"""

import sqlite3
import json
import re
from datetime import datetime
from typing import List, Dict, Optional
import os


class DatabaseManager:
    """Manages database operations for PDF documents"""
    
    def __init__(self, db_path: str = "pdfstream.db"):
        """Initialize database connection"""
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)
    
    def init_database(self):
        """Initialize database schema"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Create documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                filepath TEXT NOT NULL,
                upload_date TEXT NOT NULL,
                file_size INTEGER,
                page_count INTEGER,
                text_content TEXT,
                keywords TEXT,
                created_at TEXT NOT NULL
            )
        """)
        
        # Create keywords table for efficient searching
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                keyword TEXT NOT NULL,
                frequency INTEGER DEFAULT 1,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            )
        """)
        
        # Create index for faster keyword searches
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_keywords 
            ON document_keywords(keyword)
        """)
        
        conn.commit()
        # Migration: add keywords_source column if missing
        cursor.execute("PRAGMA table_info(documents)")
        cols = [row[1] for row in cursor.fetchall()]
        if 'keywords_source' not in cols:
            try:
                cursor.execute("ALTER TABLE documents ADD COLUMN keywords_source TEXT")
                conn.commit()
            except Exception:
                pass
        conn.close()
    
    def add_document(self, filename: str, filepath: str, file_size: int, 
                     page_count: int, text_content: str, keywords: List[str], keywords_source: str = 'extracted') -> int:
        """Add a new document to the database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        keywords_json = json.dumps(keywords)
        
        cursor.execute("""
            INSERT INTO documents 
            (filename, filepath, upload_date, file_size, page_count, text_content, keywords, created_at, keywords_source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (filename, filepath, now, file_size, page_count, text_content, keywords_json, now, keywords_source))
        
        document_id = cursor.lastrowid
        
        # Add keywords to separate table
        # Build frequency map using lowercase for indexing/search, but keep
        # original-case keywords in the documents table JSON for display.
        keyword_freq = {}
        for keyword in keywords:
            k_lc = (keyword or '').lower()
            if not k_lc:
                continue
            keyword_freq[k_lc] = keyword_freq.get(k_lc, 0) + 1
        
        for keyword, freq in keyword_freq.items():
            cursor.execute("""
                INSERT INTO document_keywords (document_id, keyword, frequency)
                VALUES (?, ?, ?)
            """, (document_id, keyword, freq))
        
        conn.commit()
        conn.close()
        
        return document_id
    
    def get_document(self, document_id: int) -> Optional[Dict]:
        """Get a document by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
                 SELECT id, filename, filepath, upload_date, file_size, page_count, 
                     text_content, keywords, created_at, keywords_source
            FROM documents WHERE id = ?
        """, (document_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row[0],
                'filename': row[1],
                'filepath': row[2],
                'upload_date': row[3],
                'file_size': row[4],
                'page_count': row[5],
                'text_content': row[6],
                'keywords': json.loads(row[7]) if row[7] else [],
                'created_at': row[8],
                'keywords_source': row[9] if len(row) > 9 else 'extracted'
            }
        return None
    
    def get_all_documents(self, limit: Optional[int] = None) -> List[Dict]:
        """Get all documents"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = """
                 SELECT id, filename, filepath, upload_date, file_size, page_count, 
                     text_content, keywords, created_at, keywords_source
            FROM documents
            ORDER BY created_at DESC
        """
        
        if limit:
            query += " LIMIT ?"
            cursor.execute(query, (limit,))
        else:
            cursor.execute(query)
        
        rows = cursor.fetchall()
        conn.close()
        
        documents = []
        for row in rows:
            documents.append({
                'id': row[0],
                'filename': row[1],
                'filepath': row[2],
                'upload_date': row[3],
                'file_size': row[4],
                'page_count': row[5],
                'text_content': row[6],
                'keywords': json.loads(row[7]) if row[7] else [],
                'created_at': row[8],
                'keywords_source': row[9] if len(row) > 9 else 'extracted'
            })
        
        return documents
    
    def delete_document(self, document_id: int) -> bool:
        """Delete a document by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Delete keywords first (cascade should handle this, but being explicit)
        cursor.execute("DELETE FROM document_keywords WHERE document_id = ?", (document_id,))
        
        # Delete document
        cursor.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        return affected > 0
    
    def search_by_keywords(self, keywords: List[str], limit: int = 10) -> List[Dict]:
        """Search documents by keywords"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        placeholders = ','.join(['?' for _ in keywords])
        
        query = f"""
            SELECT d.id, d.filename, d.filepath, d.upload_date, d.file_size, 
                   d.page_count, d.text_content, d.keywords, d.created_at,
                   COUNT(DISTINCT dk.keyword) as match_count
            FROM documents d
            JOIN document_keywords dk ON d.id = dk.document_id
            WHERE dk.keyword IN ({placeholders})
            GROUP BY d.id
            ORDER BY match_count DESC, d.created_at DESC
            LIMIT ?
        """
        
        cursor.execute(query, keywords + [limit])
        rows = cursor.fetchall()
        conn.close()
        
        documents = []
        for row in rows:
            documents.append({
                'id': row[0],
                'filename': row[1],
                'filepath': row[2],
                'upload_date': row[3],
                'file_size': row[4],
                'page_count': row[5],
                'text_content': row[6],
                'keywords': json.loads(row[7]) if row[7] else [],
                'created_at': row[8],
                'match_count': row[9]
            })
        
        return documents

    def search_by_keywords_approx(self, raw_query: str, limit: int = 100) -> List[Dict]:
        """Approximate keyword search.
        Splits the raw query into tokens (words), ignores very short tokens (<2 chars),
        and matches any stored keyword containing a token as a substring (case-insensitive).
        Returns documents ranked by number of distinct matched keywords then recency.
        """
        if not raw_query or not raw_query.strip():
            return []
        # Tokenize: split on non-alphanumeric boundaries
        tokens = [t.lower() for t in re.split(r"[^A-Za-z0-9]+", raw_query) if t and len(t) >= 2]
        if not tokens:
            return []
        conn = self.get_connection()
        cursor = conn.cursor()
        # Build dynamic LIKE conditions
        like_clauses = []
        params = []
        for tok in tokens:
            like_clauses.append("dk.keyword LIKE ?")
            params.append(f"%{tok}%")
        where_clause = " OR ".join(like_clauses)
        query = f"""
            SELECT d.id, d.filename, d.filepath, d.upload_date, d.file_size,
                   d.page_count, d.text_content, d.keywords, d.created_at,
                   COUNT(DISTINCT dk.keyword) as match_count
            FROM documents d
            JOIN document_keywords dk ON d.id = dk.document_id
            WHERE {where_clause}
            GROUP BY d.id
            ORDER BY match_count DESC, d.created_at DESC
            LIMIT ?
        """
        params.append(limit)
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        documents = []
        for row in rows:
            documents.append({
                'id': row[0],
                'filename': row[1],
                'filepath': row[2],
                'upload_date': row[3],
                'file_size': row[4],
                'page_count': row[5],
                'text_content': row[6],
                'keywords': json.loads(row[7]) if row[7] else [],
                'created_at': row[8],
                'match_count': row[9]
            })
        return documents
    
    def get_document_count(self) -> int:
        """Get total number of documents"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM documents")
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def get_all_texts(self) -> List[str]:
        """Return list of all non-empty document text_content strings for corpus-level analysis."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT text_content FROM documents WHERE text_content IS NOT NULL AND LENGTH(text_content) > 0")
        rows = cursor.fetchall()
        conn.close()
        return [r[0] for r in rows if r and r[0]]

    def update_document_keywords(self, document_id: int, keywords: List[str]) -> bool:
        """Update keywords for a document, replacing JSON list and keyword index.
        Preserves original casing in documents table; indexes lowercase.
        """
        if not isinstance(keywords, list):
            return False
        # Normalize incoming list: strip, remove empties, dedupe preserving order
        cleaned = []
        seen = set()
        for k in keywords:
            if not isinstance(k, str):
                continue
            t = k.strip()
            if not t:
                continue
            tl = t.lower()
            if tl in seen:
                continue
            seen.add(tl)
            cleaned.append(t)
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # Verify document exists
            cursor.execute("SELECT id FROM documents WHERE id = ?", (document_id,))
            if not cursor.fetchone():
                conn.close()
                return False
            # Update documents table JSON field
            cursor.execute("UPDATE documents SET keywords = ? WHERE id = ?", (json.dumps(cleaned), document_id))
            # Replace keyword index rows
            cursor.execute("DELETE FROM document_keywords WHERE document_id = ?", (document_id,))
            freq = {}
            for k in cleaned:
                kl = k.lower()
                freq[kl] = freq.get(kl, 0) + 1
            for kw_lc, f in freq.items():
                cursor.execute("INSERT INTO document_keywords (document_id, keyword, frequency) VALUES (?, ?, ?)", (document_id, kw_lc, f))
            conn.commit()
            conn.close()
            return True
        except Exception:
            conn.rollback()
            conn.close()
            return False

    def update_document_keywords_with_source(self, document_id: int, keywords: List[str], keywords_source: str) -> bool:
        """Update both keywords and keywords_source for a document."""
        ok = self.update_document_keywords(document_id, keywords)
        if not ok:
            return False
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE documents SET keywords_source = ? WHERE id = ?", (keywords_source, document_id))
            conn.commit()
            conn.close()
            return True
        except Exception:
            conn.rollback()
            conn.close()
            return False
