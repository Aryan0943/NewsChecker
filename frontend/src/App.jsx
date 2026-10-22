
import { useState } from 'react'
import './App.css'

function App() {
  // Store the topic entered by the user.
  const [topic, setTopic] = useState('')
  const [articles, setArticles] = useState([])

  // Handle search form submission.
  async function handleSearch(event) {
    if (!topic.trim()) {
      return
    }
    event.preventDefault()

    
    const response = await fetch('http://127.0.0.1:8000/analyze', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        mode: 'topic',
        content: topic,
      }),
    })

    const data = await response.json()
    setArticles(data.related_news ?? [])
    

  }

  return (
    <div className="app">
      <header className="header">
        <h1>NewsChecker</h1>
        <p>News Bias &amp; Fact-Check Platform</p>
      </header>

      <main className="main">
        <h2>Explore the news</h2>

        <p>
          Search a topic to discover related news articles
          and examine different perspectives.
        </p>

        <form className="search-form" onSubmit={handleSearch}>
          <input
            type="text"
            placeholder="Enter a topic, e.g. climate change"
            aria-label="News topic"
            value={topic}
            onChange={(event) => setTopic(event.target.value)}
          />

          <button type="submit">
            Search News
          </button>
        </form>
        
        <section className="results">
          <h2>News Results</h2>

          {articles.length === 0 ? (
            <p>No articles to display yet. Search for a topic above.</p>
          ) : (
            articles.map((article) => (
              <article key={article.url} className="article-card">
                <h3>{article.title}</h3>

                <p>Source: {article.source || 'Unknown source'}</p>

                <p>
                  Published: {article.published_at || 'Date unavailable'}
                </p>

                <a href={article.url} target="_blank" rel="noreferrer">
                  Read article
                </a>
              </article>
            ))
          )}
        </section>

      </main>
    </div>
  )
}

export default App
