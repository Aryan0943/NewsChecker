
import ArticleCard from './ArticleCard'

function NewsResults({ articles, isLoading, error, hasSearched }) {
  return (
    <section className="results">
      <div className="results-header">
        <div>
          <h2>News Results</h2>
          <p className="results-description">
            Explore coverage and compare different perspectives.
          </p>
        </div>

        {hasSearched && !isLoading && !error && (
          <span className="results-count">
            {articles.length} {articles.length === 1 ? 'article' : 'articles'}
          </span>
        )}
      </div>

      {isLoading && (
        <div className="results-state" role="status">
          <span className="loading-spinner" aria-hidden="true" />
          <p>Searching for articles...</p>
        </div>
      )}

      {!isLoading && error && (
        <div className="results-state error-state" role="alert">
          <strong>We couldn't load the news</strong>
          <p>{error}</p>
          <p>Please check your connection and try again.</p>
        </div>
      )}

      {!isLoading && !error && hasSearched && articles.length === 0 && (
        <div className="results-state">
          <h3>No articles found</h3>
          <p>Try another topic or use a more specific search phrase.</p>
        </div>
      )}

      {!isLoading && !error && articles.length > 0 && (
        <div className="articles-list">
          {articles.map((article) => (
            <ArticleCard key={article.url} article={article} />
          ))}
        </div>
      )}

      {!isLoading && !error && !hasSearched && (
        <div className="results-state welcome-state">
          <h3>Ready to explore?</h3>
          <p>
            Search for a topic above to discover related news articles.
          </p>
        </div>
      )}
    </section>
  )
}

export default NewsResults
