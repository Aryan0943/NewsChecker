
function SearchForm({
  topic,
  setTopic,
  onSearch,
  isLoading,
}) {
  return (
    <form className="search-form" onSubmit={onSearch}>
      <input
        type="text"
        placeholder="Enter a topic, e.g. climate change"
        aria-label="News topic"
        value={topic}
        onChange={(event) => setTopic(event.target.value)}
      />

      <button type="submit" disabled={isLoading}>
        {isLoading ? 'Searching...' : 'Search News'}
      </button>
    </form>
  )
}

export default SearchForm
