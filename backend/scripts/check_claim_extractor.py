
from app.services.article_fetcher import extract_article_text
from app.services.claim_extractor import extract_claims_llm


def main():

    print("=" * 65)
    print("           NEWSCHECKER - CLAIM EXTRACTION TEST")
    print("=" * 65)

    # Enter the URL of a real news article.
    article_url = input("\nEnter article URL: ").strip()

    if not article_url:
        print("Error: Article URL cannot be empty.")
        return

    try:
        # STEP 1: Fetch the article.
        print("\n[1/3] Fetching article...")

        article = extract_article_text(article_url)

        article_title = article.get("title") or "Unknown title"
        article_text = article.get("text", "")
        article_date = article.get("published_date")

        print("\nArticle fetched successfully!")
        print("Title:", article_title)
        print("URL:", article.get("url"))
        print("Article text length:", len(article_text))

        if not article_text.strip():
            print("Error: No article text was extracted.")
            return

        print("\nArticle preview:")
        print("-" * 65)
        print(article_text[:700])
        print("-" * 65)

        # STEP 2: Extract claims using Gemini.
        print("\n[2/3] Extracting claims using Gemini...")

        claims = extract_claims_llm(
            article_text=article_text,
            article_title=article_title,
            publish_date=article_date,
            max_claims=5,
        )

        # STEP 3: Display the results.
        print("\n[3/3] EXTRACTION RESULTS")
        print("=" * 65)

        if not claims:
            print("No claims were extracted.")
            print(
                "Check the article content, Gemini response "
                "and fallback extractor."
            )
            return

        for index, claim in enumerate(claims, start=1):

            print(f"\nCLAIM {index}")
            print("-" * 65)

            print("ID:", claim.claim_id)
            print("Type:", claim.claim_type)

            print("Centrality:", claim.centrality)
            print("Checkable:", claim.checkable)
            print("Grounding status:", claim.grounding_status)
            print("Validation notes:", claim.validation_notes)  

            print("\nOriginal sentence:")
            print(claim.source_sentence)

            print("\nStandalone claim:")
            print(claim.claim_text)

            print("\nEntities:", claim.entities)
            print("Location:", claim.location)
            print("Time reference:", claim.time_reference)
            print("Numbers:", claim.numbers)

            print("-" * 65)

        print("\nTotal claims extracted:", len(claims))

        # Display whether the results came from fallback IDs.
        fallback_count = sum(
            claim.claim_id.startswith("F")
            for claim in claims
        )

        if fallback_count:
            print(
                "Warning: Fallback extraction was used. "
                "Fallback claims:",
                fallback_count,
            )
        else:
            print("Extraction source: Gemini")

    except Exception as error:
        print("\nERROR:", str(error))


if __name__ == "__main__":
    main()
