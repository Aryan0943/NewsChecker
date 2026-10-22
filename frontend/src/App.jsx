
import { useState } from 'react'
import './App.css'
import { searchNews } from './services/api'
import ArticleCard from './components/ArticleCard'
import SearchForm from './components/SearchForm'
function App() {
  // Store the topic entered by the user.
  const [topic, setTopic] = useState('')
  const [articles, setArticles] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [hasSearched, setHasSearched] = useState(false)

  // Handle search form submission.
  async function handleSearch(event) {
    
    event.preventDefault()
    const searchTopic = topic.trim()
    if (!searchTopic) {
      setError('Please enter a topic to search.')
      setArticles([])
      setHasSearched(false)
      return
    }
    setIsLoading(true)
    setError('')
    setHasSearched(true)
    setArticles([])
    
    try {

      const data = await searchNews(searchTopic)
      setArticles(data.related_news ?? [])

    } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : 'Could not connect to the backend.'
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

        <p>
          Search a topic to discover related news articles
          and examine different perspectives.
        </p>

        <SearchForm
          topic={topic}
          setTopic={setTopic}
          onSearch={handleSearch}
          isLoading={isLoading}
        />
                
        
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


      </main>
    </div>
  )
}

export default App
