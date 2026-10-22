
function ArticleCard({ article }) {
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
    </article>
  )
}

export default ArticleCard
