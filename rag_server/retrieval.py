import re
from typing import List
from functools import lru_cache
from rank_bm25 import BM25Okapi
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

try:
    from underthesea import word_tokenize
    HAVE_UNDERTHESEA = True
except ImportError:
    HAVE_UNDERTHESEA = False

def remove_vietnamese_accents(text: str) -> str:
    s = text.lower()
    s = re.sub(r'[àáạảãâầấậẩẫăằắặẳẵ]', 'a', s)
    s = re.sub(r'[èéẹẻẽêềếệểễ]', 'e', s)
    s = re.sub(r'[ìíịỉĩ]', 'i', s)
    s = re.sub(r'[òóọỏõôồốộổỗơờớợởỡ]', 'o', s)
    s = re.sub(r'[ùúụủũưừứựửữ]', 'u', s)
    s = re.sub(r'[ỳýỵỷỹ]', 'y', s)
    s = re.sub(r'đ', 'd', s)
    return s


def tokenize_vn(text: str) -> List[str]:
    clean_text = re.sub(r'[^\w\s\.\-]', " ", text).lower()
    if HAVE_UNDERTHESEA:
        try:
            tokens = word_tokenize(clean_text, format="text").split()
            return tokens
        except Exception:
            pass
    return clean_text.split()

@lru_cache(maxsize=5000)
def get_cache_tokens(text: str) -> List[str]:
    tokens = tokenize_vn(text)
    return [remove_vietnamese_accents(t) for t in tokens]

def retrieve_top_chunks(query: str, chunks_data: list[dict], top = 5) -> List[dict]:
    if not chunks_data:
        return []
    corpus = [chunk['content'] for chunk in chunks_data]
    
    q_tokens = get_cache_tokens(query)
    corpus_tokens = [get_cache_tokens(doc) for doc in corpus]
    
    bm25 = BM25Okapi(corpus_tokens)
    bm25_scores = bm25.get_scores(q_tokens)
    
    bm25_ranks = {
        idx: rank + 1
        for rank, idx in enumerate(np.argsort(bm25_scores)[::-1])
    }
    
    corpus_joined = [" ".join(tokens) for tokens in corpus_tokens]
    query_joined = " ".join(q_tokens)
    
    try:
        vectorizer = TfidfVectorizer(ngram_range=(1,2), max_features=30000,token_pattern=r"(?u)[^\s]+")
        ifidf_matrix = vectorizer.fit_transform(corpus_joined)
        q_vec = vectorizer.transform([query_joined])
        cos_sim = cosine_similarity(q_vec,ifidf_matrix)[0]
    except ValueError:
        cos_sim = np.zeros(len(corpus))
    
    tfidf_ranks = {
        idx: rank + 1
        for rank, idx in enumerate(np.argsort(cos_sim)[::-1])
    }
    
    fused_score = {}
    for idx in range(len(corpus)):
        bm25_r = bm25_ranks.get(idx,999)
        tfidf_r = tfidf_ranks.get(idx,999)
        score = (1.0/(60.0 + bm25_r)) + (1.0/(60.0 + tfidf_r))
        fused_score[idx] = score
    
    ranked_indices = [
        idx for idx, _ in sorted(fused_score.items(), key=lambda x: x[1], reverse=True)[:top]
    ]
    
    return [chunks_data[i] for i in ranked_indices]

