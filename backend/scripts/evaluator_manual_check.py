import json

from app.services.evidence_retriever import search_evidence
from app.services.source_analyzer import analyze_sources
from app.services.evidence_evaluator import evaluate_evidence


claim = (
    "529 garment factories were closed "
    "in Bangladesh due to worker protests."
)

print("\nSearching for evidence...\n")

evidence = search_evidence(
    claim=claim,
    max_results=5,
    context="Bangladesh garment workers wage protests Dhaka"
)

print("Retrieved sources:", len(evidence))

if not evidence:
    print("No evidence available.")

else:

    print("\nAnalyzing source relationships...\n")

    source_analysis = analyze_sources(evidence)

    print(
        "Similarity relationships:",
        len(source_analysis["similarity_groups"])
    )

    print(
        "Attribution relationships:",
        len(source_analysis["attribution_relationships"])
    )

    print("\nEvaluating evidence using Gemini...\n")

    result = evaluate_evidence(
        claim=claim,
        evidence=evidence,
        source_analysis=source_analysis
    )

    print("\n" + "=" * 60)
    print("FINAL FACT-CHECK RESULT")
    print("=" * 60)

    print(json.dumps(
        result,
        indent=4,
        ensure_ascii=False
    ))