import { useState } from 'react'
import './App.css'

import {
  searchNews,
  analyzeArticle,
  analyzeArticleText,
} from './services/api'

import ArticleCard from './components/ArticleCard'
import SearchForm from './components/SearchForm'
import NewsResults from './components/NewsResults'

function App() {
  const [mode, setMode] = useState('topic')
  const [input, setInput] = useState('')
  const [articles, setArticles] = useState([])
  const [analysis, setAnalysis] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [hasSubmitted, setHasSubmitted] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    const content = input.trim()

    if (!content) {
      setError('Please enter a topic, URL, or article text.')
      return
    }

    setIsLoading(true)
    setError('')
    setArticles([])
    setAnalysis(null)
    setHasSubmitted(true)

    try {
      if (mode === 'topic') {
        const data = await searchNews(content)

        if (!Array.isArray(data.related_news)) {
          throw new Error('The server returned an invalid article list.')
        }

        setArticles(data.related_news)
      } else {
        const data =
          mode === 'url'
            ? await analyzeArticle(content)
            : await analyzeArticleText(content)

        setAnalysis(data)
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Something went wrong. Please try again.'
      )
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="app">
      <header className="header">
        <h1>NewsChecker</h1>
        <p>News Bias &amp; Fact-Check Platform</p>
      </header>

      <main className="main">
        <h2>Explore the news</h2>
        <p>Search news topics or analyze an article directly.</p>

        <div className="mode-selector" aria-label="Analysis mode">
          {[
            ['topic', 'Search topic'],
            ['url', 'Article URL'],
            ['text', 'Paste text'],
          ].map(([value, label]) => (
            <button
              key={value}
              type="button"
              className={mode === value ? 'mode-button active' : 'mode-button'}
              aria-pressed={mode === value}
              onClick={() => {
                setMode(value)
                setInput('')
                setError('')
                setArticles([])
                setAnalysis(null)
                setHasSubmitted(false)
              }}
            >
              {label}
            </button>
          ))}
        </div>

        <form className="search-form" onSubmit={handleSubmit}>
          {mode === 'text' ? (
            <textarea
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="Paste the article text here..."
              aria-label="Article text"
              rows={5}
              required
              disabled={isLoading}
            />
          ) : (
            <input
              type={mode === 'url' ? 'url' : 'text'}
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder={
                mode === 'url'
                  ? 'https://example.com/news/article'
                  : 'Enter a topic, e.g. climate change'
              }
              aria-label={mode === 'url' ? 'Article URL' : 'News topic'}
              required
              disabled={isLoading}
            />
          )}

          <button type="submit" disabled={isLoading || !input.trim()}>
            {isLoading
              ? 'Processing...'
              : mode === 'topic'
                ? 'Search News'
                : 'Analyze Article'}
          </button>
        </form>

        {mode === 'topic' && (
          <NewsResults
            articles={articles}
            isLoading={isLoading}
            error={error}
            hasSearched={hasSubmitted}
          />
        )}

        {mode !== 'topic' && error && (
          <p className="form-error" role="alert">{error}</p>
        )}

        {mode !== 'topic' && analysis && (
          <section className="article-analysis">
            <h3>Analysis Results</h3>
            <p>{analysis.message}</p>

            {analysis.article_title && (
              <h4>{analysis.article_title}</h4>
            )}

            {analysis.article_text && (
              <details>
                <summary>View extracted article text</summary>
                <p>{analysis.article_text}</p>
              </details>
            )}

            <h4>Bias Analysis</h4>
            {analysis.biases?.length ? (
              analysis.biases.map((bias, index) => (
                <p key={`${bias.category || 'bias'}-${index}`}>
                  <strong>{bias.category}:</strong> {bias.status}
                </p>
              ))
            ) : (
              <p>No bias results available.</p>
            )}

            <h4>Fact-Check</h4>
            <p>
              <strong>Status:</strong>{' '}
              {analysis.fact_check?.status || 'pending'}
            </p>
            <p>{analysis.fact_check?.summary}</p>
          </section>
        )}
      </main>
    </div>
  )
}

export default App
