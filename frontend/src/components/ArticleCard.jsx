
import { useState } from 'react'
import { analyzeArticle } from '../services/api'

function ArticleCard({ article }) {
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [error, setError] = useState('')
  const [analysis, setAnalysis] = useState(null)

  async function handleAnalyze() {
    setIsAnalyzing(true)
    setError('')
    setAnalysis(null)

    try {
      const result = await analyzeArticle(article.url)
      setAnalysis(result)
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Could not analyze this article.'
      )
    } finally {
      setIsAnalyzing(false)
    }
  }

  return (
    <article className="article-card">
      <div className="article-card-header">
        <span className="article-source">
          {article.source || 'Unknown source'}
        </span>

        <span className="article-date">
          {article.published_at || 'Date unavailable'}
        </span>
      </div>

      <h3>{article.title || 'Untitled article'}</h3>

      <div className="article-actions">
        <a
          className="read-article-link"
          href={article.url}
          target="_blank"
          rel="noopener noreferrer"
        >
          Read original article ↗
        </a>

        <button
          type="button"
          onClick={handleAnalyze}
          disabled={isAnalyzing}
        >
          {isAnalyzing ? 'Analyzing...' : 'Analyze Article'}
        </button>
      </div>

      {error && (
        <div className="article-error" role="alert">
          <strong>Analysis failed</strong>
          <p>{error}</p>
        </div>
      )}

      {analysis && (
        <section className="article-analysis" aria-live="polite">
          <h4>Analysis Results</h4>

          <p className="analysis-message">
            {analysis.message || 'Analysis response received.'}
          </p>

          {analysis.article_title && (
            <p>
              <strong>Extracted title:</strong> {analysis.article_title}
            </p>
          )}

          {analysis.article_text && (
            <p>
              <strong>Extracted text:</strong>{' '}
              {analysis.article_text.length.toLocaleString()} characters
            </p>
          )}

          <div className="bias-results">
            <h5>Bias Analysis</h5>

            {analysis.biases?.length > 0 ? (
              analysis.biases.map((bias, index) => (
                <div
                  className="bias-item"
                  key={`${bias.category || 'category'}-${index}`}
                >
                  <strong>{bias.category || 'Uncategorized'}</strong>
                  <span className="status-label">
                    {bias.status || 'pending'}
                  </span>
                  {bias.explanation && <p>{bias.explanation}</p>}
                </div>
              ))
            ) : (
              <p>No bias results available.</p>
            )}
          </div>

          <div className="fact-check-results">
            <h5>Fact-Check</h5>

            <p>
              <strong>Status:</strong>{' '}
              {analysis.fact_check?.status || 'pending'}
            </p>

            <p>
              {analysis.fact_check?.summary ||
                'No fact-check summary is available.'}
            </p>

            {analysis.fact_check?.sources?.length > 0 && (
              <ul>
                {analysis.fact_check.sources.map((source, index) => (
                  <li key={`${source}-${index}`}>{source}</li>
                ))}
              </ul>
            )}
          </div>
        </section>
      )}
    </article>
  )
}

export default ArticleCard
