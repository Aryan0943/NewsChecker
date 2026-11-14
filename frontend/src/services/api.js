
const API_BASE_URL = 'http://127.0.0.1:8000'

async function handleResponse(response, defaultMessage) {
  if (!response.ok) {
    let message = defaultMessage

    try {
      const data = await response.json()
      message = data.detail || message
    } catch {
      // Keep default error message.
    }

    throw new Error(message)
  }

  return response.json()
}

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

  return handleResponse(
    response,
    'The news search failed. Please try again.'
  )
}

export async function analyzeArticle(url, analysisMode = 'both') {
  const response = await fetch(`${API_BASE_URL}/analyze`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      mode: 'url',
      content: url,
      analysis_mode: analysisMode,
    }),
  })

  return handleResponse(
    response,
    'Could not analyze this article. Please try again.'
  )
}

export async function analyzeArticleText(text, analysisMode = 'both') {
  const response = await fetch(`${API_BASE_URL}/analyze`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      mode: 'text',
      content: text,
      analysis_mode: analysisMode,
    }),
  })

  return handleResponse(
    response,
    'Could not analyze the article text. Please try again.'
  )
}
