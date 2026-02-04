#!/usr/bin/env python3
"""Semantic search over documentation using BM25 (Plan #289 Phase 2).

Simple but effective keyword-based search. No ML dependencies.

Usage:
    python scripts/semantic_doc_search.py "owner artifact permission"
    python scripts/semantic_doc_search.py --file src/world/artifacts.py
    python scripts/semantic_doc_search.py --terms "owner,created_by,artifact"
"""

import argparse
import json
import math
import re
import sys
from pathlib import Path


def get_repo_root() -> Path:
    """Get repository root directory."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".git").exists():
            return parent
    return Path.cwd()


REPO_ROOT = get_repo_root()


def tokenize(text: str) -> list[str]:
    """Simple tokenization matching build_doc_index.py."""
    text = text.lower()
    tokens = re.split(r'[^a-z0-9_]+', text)
    return [t for t in tokens if len(t) > 2]


class BM25:
    """Simple BM25 implementation without external dependencies."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus: list[list[str]] = []
        self.doc_lengths: list[int] = []
        self.avg_doc_length: float = 0
        self.doc_freqs: dict[str, int] = {}  # term -> doc count
        self.idf: dict[str, float] = {}
        self.n_docs: int = 0

    def fit(self, corpus: list[list[str]]) -> None:
        """Fit BM25 on tokenized corpus."""
        self.corpus = corpus
        self.n_docs = len(corpus)
        self.doc_lengths = [len(doc) for doc in corpus]
        self.avg_doc_length = sum(self.doc_lengths) / self.n_docs if self.n_docs > 0 else 0

        # Calculate document frequencies
        self.doc_freqs = {}
        for doc in corpus:
            seen = set()
            for term in doc:
                if term not in seen:
                    self.doc_freqs[term] = self.doc_freqs.get(term, 0) + 1
                    seen.add(term)

        # Calculate IDF
        self.idf = {}
        for term, df in self.doc_freqs.items():
            # BM25 IDF formula
            self.idf[term] = math.log((self.n_docs - df + 0.5) / (df + 0.5) + 1)

    def score(self, query_tokens: list[str], doc_idx: int) -> float:
        """Calculate BM25 score for a single document."""
        doc = self.corpus[doc_idx]
        doc_len = self.doc_lengths[doc_idx]
        score = 0.0

        # Count term frequencies in document
        tf_doc: dict[str, int] = {}
        for term in doc:
            tf_doc[term] = tf_doc.get(term, 0) + 1

        for term in query_tokens:
            if term not in self.idf:
                continue
            tf = tf_doc.get(term, 0)
            if tf == 0:
                continue

            idf = self.idf[term]
            # BM25 scoring formula
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (1 - self.b + self.b * doc_len / self.avg_doc_length)
            score += idf * numerator / denominator

        return score

    def search(self, query_tokens: list[str], top_k: int = 10) -> list[tuple[int, float]]:
        """Search for top-k documents matching query."""
        scores = []
        for i in range(self.n_docs):
            score = self.score(query_tokens, i)
            if score > 0:
                scores.append((i, score))

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


def load_index(index_path: Path) -> dict:
    """Load the document index."""
    with open(index_path) as f:
        return json.load(f)


def search_docs(query: str, index: dict, top_k: int = 10) -> list[dict]:
    """Search documents for query string."""
    # Build BM25 from index
    documents = index["documents"]
    corpus = [doc["tokens"] for doc in documents]

    bm25 = BM25()
    bm25.fit(corpus)

    # Search
    query_tokens = tokenize(query)
    results = bm25.search(query_tokens, top_k)

    # Return enriched results
    return [
        {
            "score": score,
            "document": documents[idx],
        }
        for idx, score in results
    ]


def extract_terms_from_file(file_path: Path) -> set[str]:
    """Extract key terms from a source file for search."""
    import ast

    terms: set[str] = set()
    try:
        content = file_path.read_text()
    except Exception:
        return terms

    # AST extraction
    try:
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                terms.add(node.name.lower())
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                terms.add(node.name.lower())
                for part in node.name.split('_'):
                    if len(part) > 2:
                        terms.add(part.lower())
            elif isinstance(node, ast.Name):
                if len(node.id) > 2:
                    terms.add(node.id.lower())
            elif isinstance(node, ast.Attribute):
                if len(node.attr) > 2:
                    terms.add(node.attr.lower())
    except SyntaxError:
        pass

    return terms


def main() -> int:
    parser = argparse.ArgumentParser(description="Semantic search over documentation")
    parser.add_argument("query", nargs="?", help="Search query string")
    parser.add_argument("--file", "-f", help="Extract terms from file and search")
    parser.add_argument("--terms", "-t", help="Comma-separated terms to search")
    parser.add_argument("--top", "-k", type=int, default=10, help="Number of results")
    parser.add_argument("--index", default="data/doc_index.json", help="Index file path")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    # Determine query
    if args.file:
        file_path = Path(args.file)
        if not file_path.is_absolute():
            file_path = REPO_ROOT / args.file
        terms = extract_terms_from_file(file_path)
        query = ' '.join(terms)
    elif args.terms:
        query = args.terms.replace(',', ' ')
    elif args.query:
        query = args.query
    else:
        parser.error("Provide a query, --file, or --terms")
        return 1

    # Load index
    index_path = REPO_ROOT / args.index
    if not index_path.exists():
        print(f"Index not found: {index_path}")
        print("Run: python scripts/build_doc_index.py")
        return 1

    index = load_index(index_path)

    # Search
    results = search_docs(query, index, args.top)

    if args.json:
        print(json.dumps(results, indent=2))
        return 0

    # Pretty print results
    print(f"Search: {query[:80]}{'...' if len(query) > 80 else ''}")
    print(f"Results: {len(results)}")
    print("-" * 60)

    for i, result in enumerate(results, 1):
        doc = result["document"]
        score = result["score"]
        doc_type = doc["type"]

        if doc_type == "adr":
            print(f"{i}. [{score:.2f}] {doc['id']}: {doc['title']}")
            if doc.get("principles"):
                print(f"   Principle: {doc['principles'][0][:60]}...")
        elif doc_type == "glossary":
            print(f"{i}. [{score:.2f}] {doc['term']}")
            print(f"   {doc['definition'][:60]}...")
        elif doc_type == "conceptual_model":
            print(f"{i}. [{score:.2f}] CONCEPT: {doc['section']}")
            print(f"   {doc['description'][:60]}...")
        elif doc_type == "architecture":
            print(f"{i}. [{score:.2f}] {doc['title']}")
            print(f"   {doc['summary'][:60]}...")

        print(f"   File: {doc['file']}")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
