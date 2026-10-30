#!/usr/bin/env python3
"""Rank strictly prior issues by deterministic TF-IDF cosine similarity."""
import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path

TOKEN = re.compile(r"[a-z0-9][a-z0-9_.-]{1,}")


def tokens(text):
    return TOKEN.findall(text.lower())


def tfidf_vectors(documents):
    counts = [Counter(tokens(doc)) for doc in documents]
    doc_freq = Counter(term for count in counts for term in count)
    total = len(documents)
    vectors = []
    for count in counts:
        vectors.append({term: freq * (math.log((1 + total) / (1 + doc_freq[term])) + 1)
                        for term, freq in count.items()})
    return vectors


def cosine(left, right):
    numerator = sum(value * right.get(term, 0.0) for term, value in left.items())
    lnorm = math.sqrt(sum(value * value for value in left.values()))
    rnorm = math.sqrt(sum(value * value for value in right.values()))
    return numerator / (lnorm * rnorm) if lnorm and rnorm else 0.0


def rank(query, prior, limit=5):
    titles = [item.get("title", item.get("title_as_of_cutoff", "")) for item in prior]
    documents = [query] + titles
    vectors = tfidf_vectors(documents)
    ranked = [{"number": item["number"], "title": titles[index],
               "score": round(cosine(vectors[0], vectors[index + 1]), 6)}
              for index, item in enumerate(prior)]
    return sorted(ranked, key=lambda item: (-item["score"], item["number"]))[:limit]


def resolve_corpus(case, corpus_root):
    """Resolve one frozen corpus by exact case title without model-chosen paths."""
    root = Path(corpus_root)
    matches = []
    for input_path in sorted(root.glob("*/input.json")):
        candidate = json.loads(input_path.read_text(encoding="utf-8"))
        if candidate.get("title") == case.get("title"):
            matches.append((input_path, candidate))
    if len(matches) != 1:
        raise ValueError(f"expected one frozen case title match, found {len(matches)}")
    input_path, candidate = matches[0]
    snapshot_name = candidate.get("duplicate_snapshot")
    if not isinstance(snapshot_name, str) or Path(snapshot_name).name != snapshot_name:
        raise ValueError("invalid duplicate snapshot name")
    return input_path.parent / snapshot_name


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", required=True, help="Prepared case JSON")
    corpus = parser.add_mutually_exclusive_group(required=True)
    corpus.add_argument("--corpus", help="Strictly prior issue snapshot")
    corpus.add_argument("--corpus-root", help="Frozen case directories; exact title selects one")
    parser.add_argument("--output", required=True)
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()
    case = json.loads(Path(args.case).read_text(encoding="utf-8"))
    corpus_path = Path(args.corpus) if args.corpus else resolve_corpus(case, args.corpus_root)
    prior = json.loads(corpus_path.read_text(encoding="utf-8"))
    # Weight the concise title above template boilerplate and long reproduction text.
    query = f"{(case.get('title', '') + ' ') * 5}{case.get('body', '')}"
    result = {"method": "tf-idf-cosine-v1", "candidates": rank(query, prior, args.limit)}
    Path(args.output).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
