
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
      <h3>{article.title}</h3>

      <p>Source: {article.source || 'Unknown source'}</p>

      <p>
        Published: {article.published_at || 'Date unavailable'}
      </p>

      <a href={article.url} target="_blank" rel="noreferrer">
        Read article
      </a>

      <div>
        <button
          type="button"
          onClick={handleAnalyze}
          disabled={isAnalyzing}
        >
          {isAnalyzing ? 'Processing...' : 'Analyze Article'}
        </button>
      </div>

      {error && <p role="alert">{error}</p>}

      {analysis && (
        <section className="article-analysis">
          <h4>Analysis Result</h4>

          <p>{analysis.message}</p>

          {analysis.article_title && (
            <p>Article title: {analysis.article_title}</p>
          )}

          {analysis.article_text && (
            <p>
              Extracted text length: {analysis.article_text.length} characters
            </p>
          )}

          
          <section className="bias-results">
            <h5>Bias Analysis</h5>

            {analysis.biases?.length > 0 ? (
              analysis.biases.map((bias) => (
                <p key={bias.category}>
                  <strong>{bias.category}:</strong> {bias.status}
                  {bias.score != null && ` (Score: ${bias.score})`}
                  {bias.explanation && ` — ${bias.explanation}`}
                </p>
              ))
            ) : (
              <p>No bias results available yet.</p>
            )}
          </section>

          <section className="fact-check-results">
            <h5>Fact-Check</h5>

            <p>
              <strong>Status:</strong>{' '}
              {analysis.fact_check?.status || 'pending'}
            </p>

            <p>
              {analysis.fact_check?.summary ||
                'Automated fact verification is not implemented yet.'}
            </p>

            {analysis.fact_check?.sources?.length > 0 && (
              <ul>
                {analysis.fact_check.sources.map((source, index) => (
                  <li key={`${source}-${index}`}>{source}</li>
                ))}
              </ul>
            )}
          </section>

        </section>
      )}
    </article>
  )
}

export default ArticleCard
