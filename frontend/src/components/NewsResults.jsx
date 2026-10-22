
import ArticleCard from './ArticleCard'

function NewsResults({ articles, isLoading, error, hasSearched }) {
  return (
    <section className="results">
      <h2>News Results</h2>

      {isLoading && <p>Searching for articles...</p>}

      {error && <p role="alert">{error}</p>}

      {!isLoading && !error && hasSearched && articles.length === 0 && (
        <p>No articles found. Try a different topic.</p>
      )}

      {!isLoading && !error && articles.length > 0 && (
        articles.map((article) => (
          <ArticleCard key={article.url} article={article} />
        ))
      )}
    </section>
  )
}

export default NewsResults
