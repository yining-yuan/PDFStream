"""
PDF processing module for PDFStream
Handles PDF text extraction and keyword extraction
"""

import os
from typing import List, Dict, Tuple, Optional
import PyPDF2
import re
from collections import Counter
import nltk
import unicodedata
from nltk.corpus import stopwords, wordnet
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from nltk import pos_tag, RegexpParser
from nltk.collocations import BigramCollocationFinder, TrigramCollocationFinder
from nltk.metrics.association import BigramAssocMeasures, TrigramAssocMeasures
from sklearn.feature_extraction.text import TfidfVectorizer


class PDFProcessor:
    """Handles PDF text extraction and keyword extraction"""
    
    def __init__(self):
        """Initialize PDF processor and download required NLTK data"""
        self._ensure_nltk_data()
        try:
            self.stop_words = set(stopwords.words('english'))
        except LookupError:
            self._ensure_nltk_data()
            self.stop_words = set(stopwords.words('english'))
        # 1125: Domain-specific stopword extension
        self.domain_stopwords = {
            'paper','method','methods','result','results','system','approach','study','analysis','data','new','novel','using','based'
        }
        self.stop_words.update(self.domain_stopwords)
        self.lemmatizer = WordNetLemmatizer()
    
    def _ensure_nltk_data(self):
        """Ensure required NLTK data is downloaded"""
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt', quiet=True)
        
        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('stopwords', quiet=True)
        try:
            nltk.data.find('corpora/wordnet')
        except LookupError:
            nltk.download('wordnet', quiet=True)
        try:
            nltk.data.find('corpora/omw-1.4')
        except LookupError:
            nltk.download('omw-1.4', quiet=True)
        try:
            nltk.data.find('taggers/averaged_perceptron_tagger')
        except LookupError:
            nltk.download('averaged_perceptron_tagger', quiet=True)
    
    def extract_text_from_pdf(self, pdf_path: str) -> Tuple[str, int]:
        """
        Extract text content from a PDF file
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Tuple of (extracted_text, page_count)
        """
        text = ""
        page_count = 0
        
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                page_count = len(pdf_reader.pages)

                for page in pdf_reader.pages:
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            cleaned = self._sanitize_surrogates(page_text)
                            text += cleaned + "\n"
                    except (PyPDF2.errors.PdfReadError, PyPDF2.errors.PyPdfError) as e:
                        print(f"Error extracting text from page: {e}")
                        continue
        except (PyPDF2.errors.PdfReadError, FileNotFoundError, PermissionError) as e:
            # Requirement: always return (text, page_count) even on errors.
            print(f"Error reading PDF file: {e}")
            return "", 0

        return text.strip(), page_count

    def _sanitize_surrogates(self, s: str) -> str:
        """Remove or safely encode surrogate code points that cause UTF-8 encoding failures.
        Strategy:
        1. Directly strip isolated surrogate code points (range D800-DFFF) which are invalid in UTF-8.
        2. Fallback encode/decode ignoring errors to ensure downstream DB/json operations succeed.
        Preserves standard BMP and non-BMP characters already correctly decoded.
        """
        # Quick removal of any surrogate code units
        # Python treats them as individual code points if decoding was imperfect.
        s_no_sur = re.sub(r'[\ud800-\udfff]', '', s)
        try:
            # Attempt round-trip to ensure safety; ignore undecodable remnants.
            return s_no_sur.encode('utf-8', 'ignore').decode('utf-8', 'ignore')
        except Exception:
            return s_no_sur.replace('\ud835', '')  # specific common problematic surrogate seen in logs

    def extract_explicit_keywords(self, text: str, max_n: int = 10) -> List[str]:
        """Explicit keyword extraction limited to at most four lines.
        Patterns supported (case-insensitive):
          Keywords: / KEYWORDS: / Key words: / Index Terms: / Index Terms—
        Captures: remainder of trigger line plus up to THREE continuation lines.
        Continuation scan stops if any line is blank, a section heading, >40 words,
        or contains a tab or double-space sequence (interpreted as start of paragraph/layout).
        Returns original-case list; [] if nothing found.
        """
        if not text:
            return []

        # Restrict search scope to early part (title + abstract region)
        snippet = text[:120000]
        raw_lines = snippet.splitlines()
        lines = [ln.strip() for ln in raw_lines]

        trigger_regex = re.compile(
            r"^(?i)(keywords?|key\s*words?|index\s*terms?)\s*(?:[:\-–—]|$)\s*(.*)$"
        )
        heading_regex = re.compile(
            r"^(?i)(abstract|introduction|materials|methods|results|discussion|"
            r"conclusions?|references|acknowledg?ments?)\b"
        )

        collected: List[str] = []
        found_index = -1

        for i, raw in enumerate(lines):
            m = trigger_regex.match(raw)
            if m:
                found_index = i
                remainder = m.group(2).strip()

                # === MAIN EARLY STOP: require "...word1; word2..." or "...word1, word2..."
                # i.e. at least one delimiter followed by another token.
                if remainder:
                    pattern_ok = bool(
                        re.search(r"\b\w[\w\-]*\s*[;,]\s+\w[\w\-]*", remainder)
                    )
                    if not pattern_ok:
                        return []  # bail out of explicit mode entirely

                    collected.append(remainder)

                # Allow up to THREE continuation lines (total 4 including trigger)
                max_continuations = 3
                for j in range(1, max_continuations + 1):
                    idx = i + j
                    if idx >= len(lines):
                        break
                    nxt_raw = raw_lines[idx]
                    nxt = lines[idx]
                    # Stop conditions
                    if not nxt:
                        break
                    if heading_regex.match(nxt):
                        break
                    if len(nxt.split()) > 40:  # likely paragraph start
                        break
                    if ("\t" in nxt_raw) or ("  " in nxt_raw):  # layout/paragraph indicator
                        break
                    collected.append(nxt)
                break

        if found_index == -1:
            return []

        # Join lines
        block = " ".join(collected)
        # Strip multiple spaces
        block = re.sub(r"\s+", " ", block).strip()

        # Heuristic: cut off classic ACM/IEEE junk if present
        block = re.split(r"(?i)\bacm reference format\b", block)[0]
        block = re.split(r"(?i)\b(ccs concepts|copyright)\b", block)[0]

        # Split by ; or , into raw candidates
        parts = [p.strip() for p in re.split(r"[;,]", block) if p.strip()]

        noise_regex = re.compile(r"^(https?://|doi\b|10\.\d{4,}/)", re.IGNORECASE)

        def clean_candidate(p: str) -> Optional[str]:
            # strip leading/trailing junk
            p2 = re.sub(r"^[\-–—\s]+", "", p)
            p2 = re.sub(r"[\s\.]+$", "", p2)
            if not p2:
                return None
            if noise_regex.search(p2):
                return None


            tokens = p2.split()
            if not tokens:
                return None
            
            # 1125: Define stop tokens indicating end of keyword phrase
            STOP_TOKENS = {
                # publisher / meta words that mean we've left the keyword list
                "acm",
                "ieee",
                "springer",
                "press",
                "university",
                "journal",
                "proceedings",
                "reference",
                "format",
                "arxiv",
                "volume",
                "vol.",
                "no.",
                "pages",
            }

            clean_tokens: List[str] = []
            for tok in tokens:
                stripped = tok.strip(",;:.")
                lower = stripped.lower()

                # stop once we hit meta tokens, years, or a colon in the middle
                if re.fullmatch(r"(19|20)\d{2}", stripped):
                    break
                if ":" in tok and clean_tokens:
                    break
                if lower in STOP_TOKENS:
                    break

                clean_tokens.append(stripped)

            if not clean_tokens:
                return None

            # Very long phrases are likely garbage (e.g. whole sentence)
            if len(clean_tokens) > 6:
                return None

            return " ".join(clean_tokens)

        cleaned: List[str] = []
        for p in parts:
            kw = clean_candidate(p)
            if not kw:
                continue
            # Avoid single very common words mistakenly captured
            if len(kw) < 3:
                continue
            cleaned.append(kw)

        # Deduplicate preserving order
        seen = set()
        result: List[str] = []
        for k in cleaned:
            kl = k.lower()
            if kl in seen:
                continue
            seen.add(kl)
            result.append(k)
            if len(result) >= max_n:
                break

        return result

    
    def extract_keywords(self, text: str, top_n: int = 10) -> List[str]:
        """
        Extract keywords from text using frequency analysis
        
        Args:
            text: Input text
            top_n: Number of top keywords to return
            
        Returns:
            List of keywords
        """
        # Convert to lowercase and remove special characters
        text = text.lower()
        text = re.sub(r'[^a-z0-9\s]', ' ', text)
        
        # Tokenize
        try:
            tokens = word_tokenize(text)
        except Exception:
            # Fallback to simple split if word_tokenize fails
            tokens = text.split()
        
        # Filter out stop words and short words
        filtered_tokens = [
            word for word in tokens 
            if word not in self.stop_words 
            and len(word) > 2
            and not word.isdigit()
        ]
        
        # Count frequencies
        word_freq = Counter(filtered_tokens)
        
        # Get top N keywords
        keywords = [word for word, _ in word_freq.most_common(top_n)]
        
        return keywords

    # --- Advanced extraction ---
    def _lemmatize_tokens(self, tokens: List[Tuple[str,str]]) -> List[str]:
        out = []
        for w, tag in tokens:
            w = w.lower()
            if w in self.stop_words or len(w) < 3 or w.isdigit():
                continue
            pos = tag[0].lower()
            wn_pos = {'n': wordnet.NOUN, 'v': wordnet.VERB, 'a': wordnet.ADJ, 'r': wordnet.ADV}.get(pos, wordnet.NOUN)
            lemma = self.lemmatizer.lemmatize(w, pos=wn_pos)
            out.append(lemma)
        return out

    def _extract_noun_phrases(self, tokens: List[Tuple[str,str]]) -> List[str]:
        grammar = r"NP: {<JJ.*>*<NN.*>+}"  # adjectives then one+ nouns
        chunker = RegexpParser(grammar)
        tree = chunker.parse(tokens)
        phrases = []
        for subtree in tree.subtrees(lambda t: t.label() == 'NP'):
            words = [w for w, _ in subtree.leaves()]
            # Basic filtering
            if len(words) > 1:
                phrase = ' '.join(w.lower() for w in words if w.lower() not in self.stop_words)
                phrase = re.sub(r'\b(?:and|or|the|of|in|on|for|with|to)\b','', phrase).strip()
                phrase = re.sub(r'\s+',' ', phrase)
                if phrase and len(phrase.split()) <= 5:
                    phrases.append(phrase)
        # Deduplicate
        seen = set()
        result = []
        for p in phrases:
            if p in seen: continue
            seen.add(p)
            result.append(p)
        return result

    def _extract_collocations(self, words: List[str]) -> List[str]:
        bigram_measures = BigramAssocMeasures()
        trigram_measures = TrigramAssocMeasures()
        bigram_finder = BigramCollocationFinder.from_words(words)
        trigram_finder = TrigramCollocationFinder.from_words(words)
        bigram_finder.apply_freq_filter(2)
        trigram_finder.apply_freq_filter(2)
        bigrams = [" ".join(bg) for bg, score in bigram_finder.score_ngrams(bigram_measures.pmi)[:15]]
        trigrams = [" ".join(tg) for tg, score in trigram_finder.score_ngrams(trigram_measures.pmi)[:10]]
        phrases = []
        for p in bigrams + trigrams:
            toks = p.split()
            if all(t in self.stop_words for t in toks):
                continue
            phrases.append(p)
        return phrases

    def extract_keywords_advanced(self, text: str, corpus_texts: Optional[List[str]] = None, top_n: int = 50) -> List[str]:
        """Advanced keyword/phrase extraction using TF-IDF across corpus + noun phrases + collocations + lemmatization + section weighting."""
        if not text or not text.strip():
            return []
        # Detect abstract section (lines after 'Abstract' until blank line)
        abstract_tokens = set()
        lines = text.splitlines()
        in_abs = False
        abs_buf = []
        for ln in lines[:400]:  # limit scanning
            if not in_abs and re.match(r'(?i)^abstract\b', ln.strip()):
                in_abs = True
                continue
            if in_abs:
                if not ln.strip():
                    break
                abs_buf.append(ln)
        abstract_text = "\n".join(abs_buf)

        # Tokenize + POS tag (limit size for performance)
        raw_tokens = word_tokenize(text[:100000])
        # Simple word filtering for tagging
        filtered_for_tag = [t for t in raw_tokens if re.match(r'[A-Za-z]{3,}$', t)]
        tagged = pos_tag(filtered_for_tag)
        lemmatized = self._lemmatize_tokens(tagged)

        # Build corpus for TF-IDF (include current text as last element)
        corpus = list(corpus_texts or [])
        corpus.append(text)
        try:
            vectorizer = TfidfVectorizer(stop_words='english', max_features=5000)
            tfidf_matrix = vectorizer.fit_transform(corpus)
            feature_names = vectorizer.get_feature_names_out()
            current_vec = tfidf_matrix[-1].toarray()[0]
        except Exception:
            # Fallback to frequency-based
            return self.extract_keywords(text, top_n)

        scores = {}
        abs_set = set(w.lower() for w in word_tokenize(abstract_text))
        for fname, score in zip(feature_names, current_vec):
            if score <= 0: continue
            base = fname.lower()
            if base in self.stop_words or len(base) < 3: continue
            boost = 1.3 if base in abs_set else 1.0
            scores[base] = score * boost

        # Collocations & noun phrases
        noun_phrases = self._extract_noun_phrases(tagged)
        collocations = self._extract_collocations(lemmatized)
        phrase_candidates = noun_phrases + collocations
        phrase_scores = {}
        for ph in phrase_candidates:
            toks = ph.split()
            # Average token scores
            tok_scores = [scores.get(t, 0) for t in toks]
            if sum(tok_scores) == 0: continue
            phrase_scores[ph] = (sum(tok_scores) / len(tok_scores)) * (1 + 0.1*len(toks))

        # Merge tokens and phrases
        token_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        phrase_items = sorted(phrase_scores.items(), key=lambda x: x[1], reverse=True)

        combined: List[str] = []
        # Interleave phrases and tokens giving preference to phrases
        p_i = 0; t_i = 0
        while len(combined) < top_n and (p_i < len(phrase_items) or t_i < len(token_items)):
            if p_i < len(phrase_items):
                ph = phrase_items[p_i][0]
                if ph not in combined:
                    combined.append(ph)
                p_i += 1
            if len(combined) >= top_n: break
            if t_i < len(token_items):
                tk = token_items[t_i][0]
                if tk not in combined:
                    combined.append(tk)
                t_i += 1

        return combined[:top_n]
    
    def process_pdf(self, pdf_path: str, top_keywords: int = 10, corpus_texts: Optional[List[str]] = None) -> Dict:
        """
        Process a PDF file: extract text and keywords
        
        Args:
            pdf_path: Path to the PDF file
            top_keywords: Number of top keywords to extract
            
        Returns:
            Dictionary with extracted data
        """
        # Extract text
        text, page_count = self.extract_text_from_pdf(pdf_path)
        
        # Prefer explicit (author-provided) keywords; fallback to extracted
        explicit = self.extract_explicit_keywords(text, max_n=top_keywords)
        if explicit:
            keywords = explicit
            keywords_source = 'explicit'
        else:
            # Advanced extraction fallback
            try:
                keywords = self.extract_keywords_advanced(text, corpus_texts=corpus_texts, top_n=top_keywords)
                keywords_source = 'advanced'
            except Exception:
                keywords = self.extract_keywords(text, top_keywords)
                keywords_source = 'extracted'
        
        # Get file info
        file_size = os.path.getsize(pdf_path)
        filename = os.path.basename(pdf_path)
        
        # 1125 : Return structured result
        return {
            'filename': filename,
            'filepath': pdf_path,
            'text': text,
            'keywords': keywords,
            'keywords_source': keywords_source,
            'page_count': page_count,
            'file_size': file_size
        }
    
    def extract_keywords_from_text(self, text: str, top_n: int = 10) -> List[str]:
        """
        Extract keywords from raw text (for search queries)
        
        Args:
            text: Input text
            top_n: Number of keywords to return
            
        Returns:
            List of keywords
        """
        return self.extract_keywords(text, top_n)
