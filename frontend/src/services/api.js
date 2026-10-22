
const API_BASE_URL = 'http://127.0.0.1:8000'

export async function searchNews(topic) {
  const response = await fetch(`${API_BASE_URL}/analyze`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      mode: 'topic',
      content: topic,
    }),
  })

  if (!response.ok) {
    let message = 'The news search failed. Please try again.'

    try {
      const data = await response.json()
      message = data.detail || message
    } catch {
      // Keep the default message if the response isn't JSON.
    }

    throw new Error(message)
  }

  return response.json()
}
