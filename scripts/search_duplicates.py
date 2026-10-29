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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Case input.json")
    parser.add_argument("--corpus", required=True, help="Strictly prior issue snapshot")
    parser.add_argument("--output", required=True)
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()
    case = json.loads(Path(args.input).read_text(encoding="utf-8"))
    prior = json.loads(Path(args.corpus).read_text(encoding="utf-8"))
    # Weight the concise title above template boilerplate and long reproduction text.
    query = f"{(case.get('title', '') + ' ') * 5}{case.get('body', '')}"
    result = {"method": "tf-idf-cosine-v1", "candidates": rank(query, prior, args.limit)}
    Path(args.output).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
