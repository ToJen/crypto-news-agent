import apiClient from './index'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp?: string
}

export interface AskRequest {
  question: string
  session_id?: string
  chat_history?: ChatMessage[]
}

export interface AskResponse {
  answer: string
  sources: NewsArticle[]
  session_id: string
  timestamp: string
}

export interface NewsArticle {
  title: string
  url: string
  source: string
  published_at: string
  content?: string
  summary?: string
}

// ask question about crypto news with streaming response
export const askQuestionStream = async (
  request: AskRequest,
  onChunk: (chunk: string) => void,
  onComplete: (sources: NewsArticle[], sessionId: string) => void,
  onError: (error: string) => void,
  signal?: AbortSignal
) => {
  try {
    const response = await fetch(`${apiClient.defaults.baseURL}/api/v1/ask`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
      signal,
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const reader = response.body?.getReader()
    const decoder = new TextDecoder()

    if (!reader) {
      throw new Error('No response body')
    }

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      const chunk = decoder.decode(value)
      const lines = chunk.split('\n')

      let currentEvent = ''
      let currentData = ''

      for (const line of lines) {
        if (line.startsWith('event: ')) {
          currentEvent = line.slice(7).trim()
        } else if (line.startsWith('data: ')) {
          currentData = line.slice(6).trim()
          
          if (currentData && currentEvent) {
            try {
              const data = JSON.parse(currentData)
              
              if (currentEvent === 'answer_chunk' && data.chunk) {
                onChunk(data.chunk)
              } else if (currentEvent === 'answer_complete' && data.sources) {
                onComplete(data.sources, data.session_id)
              } else if (currentEvent === 'error') {
                onError(data.error || 'Unknown error')
              }
            } catch (e) {
              console.error('Error parsing SSE data:', e)
            }
          }
        }
      }
    }
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      onError('Request cancelled')
    } else {
      onError(error instanceof Error ? error.message : 'Unknown error')
    }
  }
}

export const healthCheck = async () => {
  const response = await apiClient.get('/health')
  return response.data
} 