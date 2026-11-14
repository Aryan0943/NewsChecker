
from app.services.evidence_retriever import search_evidence

results = search_evidence(
    "Bangladesh garment factories closed November 2026 "
    "worker wage protests number of factories suspended"
)

for i, result in enumerate(results, start=1):

    print(f"\n{'=' * 60}")
    print(f"RESULT {i}")
    print(f"{'=' * 60}")

    print("Title:", result["title"])
    print("Domain:", result["domain"])
    print("URL:", result["url"])
    print("Published:", result["published_date"])
    print("Relevance:", result["relevance_score"])
    print("Content:", result["content"][:500])
