print("TEST SCRIPT STARTED")

from app.services.evidence_retriever import search_evidence
from app.services.source_analyzer import analyze_sources

print("Imports successful")

claim = (
    "529 garment factories were closed "
    "in Bangladesh due to worker protests."
)

print("Searching for evidence...")

evidence = search_evidence(claim, max_results=5)

print("Evidence retrieved:", len(evidence))

print("Running source analyzer...")

result = analyze_sources(evidence)

print("\nSOURCE ANALYSIS RESULT")
print("=" * 60)

print("Unique sources:", result["unique_source_count"])

print("\nSimilarity groups:")
for group in result["similarity_groups"]:
    print(group)

print("\nAttribution relationships:")
for relationship in result["attribution_relationships"]:
    print(relationship)

print("\nTEST SCRIPT COMPLETED")