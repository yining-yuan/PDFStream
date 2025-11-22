"""
ML matching module for PDFStream
Handles document similarity matching using TF-IDF and cosine similarity
"""

from typing import List, Dict, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


class MLMatcher:
    """Handles ML-based document matching using TF-IDF and cosine similarity"""
    
    def __init__(self):
        """Initialize ML matcher"""
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2),  # Use unigrams and bigrams
            min_df=1
        )
        self.document_vectors = None
        self.document_ids = []
    
    def fit_documents(self, documents: List[Dict]):
        """
        Fit the vectorizer on a collection of documents
        
        Args:
            documents: List of document dictionaries with 'id' and 'text_content'
        """
        if not documents:
            self.document_vectors = None
            self.document_ids = []
            return
        
        # Extract text content
        texts = []
        ids = []
        
        for doc in documents:
            text = doc.get('text_content', '')
            if text and text.strip():
                texts.append(text)
                ids.append(doc['id'])
        
        if not texts:
            self.document_vectors = None
            self.document_ids = []
            return
        
        # Create TF-IDF vectors
        self.document_vectors = self.vectorizer.fit_transform(texts)
        self.document_ids = ids
    
    def find_similar_documents(self, query_text: str, top_n: int = 10) -> List[Tuple[int, float]]:
        """
        Find documents similar to the query text
        
        Args:
            query_text: Text to search for
            top_n: Number of top matches to return
            
        Returns:
            List of tuples (document_id, similarity_score)
        """
        if self.document_vectors is None or not query_text.strip():
            return []
        
        # Transform query text
        try:
            query_vector = self.vectorizer.transform([query_text])
        except Exception as e:
            print(f"Error transforming query: {e}")
            return []
        
        # Calculate cosine similarities
        similarities = cosine_similarity(query_vector, self.document_vectors)[0]
        
        # Get top N similar documents
        top_indices = np.argsort(similarities)[::-1][:top_n]
        
        results = []
        for idx in top_indices:
            score = float(similarities[idx])
            if score > 0:  # Only include documents with positive similarity
                doc_id = self.document_ids[idx]
                results.append((doc_id, score))
        
        return results
    
    def find_similar_to_document(self, document_id: int, top_n: int = 10) -> List[Tuple[int, float]]:
        """
        Find documents similar to a specific document
        
        Args:
            document_id: ID of the document to compare against
            top_n: Number of top matches to return
            
        Returns:
            List of tuples (document_id, similarity_score)
        """
        if self.document_vectors is None or document_id not in self.document_ids:
            return []
        
        # Get the index of the document
        try:
            doc_index = self.document_ids.index(document_id)
        except ValueError:
            return []
        
        # Get the document vector
        doc_vector = self.document_vectors[doc_index]
        
        # Calculate cosine similarities with all documents
        similarities = cosine_similarity(doc_vector, self.document_vectors)[0]
        
        # Get top N similar documents (excluding itself)
        top_indices = np.argsort(similarities)[::-1][:top_n + 1]
        
        results = []
        for idx in top_indices:
            if self.document_ids[idx] == document_id:
                continue  # Skip the document itself
            
            score = float(similarities[idx])
            if score > 0:
                results.append((self.document_ids[idx], score))
            
            if len(results) >= top_n:
                break
        
        return results
    
    def get_document_keywords_tfidf(self, document_text: str, top_n: int = 20) -> List[Tuple[str, float]]:
        """
        Extract important keywords from a document using TF-IDF scores
        
        Args:
            document_text: Document text
            top_n: Number of top keywords to return
            
        Returns:
            List of tuples (keyword, tfidf_score)
        """
        if not document_text.strip():
            return []
        
        # Create a temporary vectorizer for this document
        temp_vectorizer = TfidfVectorizer(
            max_features=top_n,
            stop_words='english',
            ngram_range=(1, 2)
        )
        
        try:
            tfidf_matrix = temp_vectorizer.fit_transform([document_text])
            feature_names = temp_vectorizer.get_feature_names_out()
            
            # Get TF-IDF scores
            scores = tfidf_matrix.toarray()[0]
            
            # Sort by score
            top_indices = np.argsort(scores)[::-1][:top_n]
            
            keywords = [(feature_names[idx], float(scores[idx])) for idx in top_indices if scores[idx] > 0]
            
            return keywords
        except Exception as e:
            print(f"Error extracting TF-IDF keywords: {e}")
            return []
