import { useState, useRef, useEffect } from 'react'
import ChatInput from '@/components/ChatInput'
import ChatMessage from '@/components/ChatMessage'
import { askQuestionStream } from '@/apis/cryptoNewsAPI'

interface ChatMessage {
  id: string
  message: string
  isUser: boolean
  timestamp: string
  sources?: any[]
  isStreaming?: boolean
}

const ChatPage = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [sessionId, setSessionId] = useState<string>('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [currentStreamingMessage, setCurrentStreamingMessage] = useState<string>('')
  const [abortController, setAbortController] = useState<AbortController | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    setSessionId(crypto.randomUUID())
  }, [])

  const handleStreamingResponse = async (question: string) => {
    setIsStreaming(true)
    setCurrentStreamingMessage('')
    
    const controller = new AbortController()
    setAbortController(controller)
    
    const tempMessageId = crypto.randomUUID()
    const tempMessage: ChatMessage = {
      id: tempMessageId,
      message: '',
      isUser: false,
      timestamp: new Date().toISOString(),
      isStreaming: true,
    }
    setMessages(prev => [...prev, tempMessage])

    try {
      // Prepare chat history for the API (exclude error messages and cancellations)
      const chatHistory = messages
        .filter(msg => {
          // Exclude error messages and cancellations from chat history
          const isError = msg.message.includes('Sorry, I encountered an error') || 
                         msg.message.includes('Generation cancelled by user')
          return !isError
        })
        .map(msg => ({
          role: msg.isUser ? 'user' as const : 'assistant' as const,
          content: msg.message,
          timestamp: msg.timestamp
        }))
      
      await askQuestionStream(
        { question, session_id: sessionId, chat_history: chatHistory },
        (chunk: string) => {
          setCurrentStreamingMessage(prev => prev + chunk)
          setMessages(prev => 
            prev.map(msg => 
              msg.id === tempMessageId 
                ? { ...msg, message: prev.find(m => m.id === tempMessageId)?.message + chunk || chunk }
                : msg
            )
          )
        },
        (sources: any[], sessionId: string) => {
          setMessages(prev => 
            prev.map(msg => 
              msg.id === tempMessageId 
                ? { ...msg, sources, isStreaming: false }
                : msg
            )
          )
          setIsStreaming(false)
          setCurrentStreamingMessage('')
          setAbortController(null)
        },
        (error: string) => {
          console.error('Error in streaming:', error)
          
          // check if this is a cancellation or actual error
          const isCancellation = error === 'Request cancelled' || error.includes('cancelled') || error.includes('aborted')
          
          setMessages(prev => 
            prev.map(msg => 
              msg.id === tempMessageId 
                ? { 
                    ...msg, 
                    message: isCancellation 
                      ? 'Generation cancelled by user.' 
                      : 'Sorry, I encountered an error while processing your question. Please try again.', 
                    isStreaming: false 
                  }
                : msg
            )
          )
          setIsStreaming(false)
          setCurrentStreamingMessage('')
          setAbortController(null)
        },
        controller.signal
      )
    } catch (error) {
      console.error('Error asking question:', error)
      
      // Check if this is a cancellation or actual error
      const isCancellation = error instanceof Error && (
        error.name === 'AbortError' || 
        error.message.includes('cancelled') || 
        error.message.includes('aborted')
      )
      
      setMessages(prev => 
        prev.map(msg => 
          msg.id === tempMessageId 
            ? { 
                ...msg, 
                message: isCancellation 
                  ? 'Generation cancelled by user.' 
                  : 'Sorry, I encountered an error while processing your question. Please try again.', 
                isStreaming: false 
              }
            : msg
        )
      )
      setIsStreaming(false)
      setCurrentStreamingMessage('')
      setAbortController(null)
    }
  }

  const handleSendMessage = (message: string) => {
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      message,
      isUser: true,
      timestamp: new Date().toISOString(),
    }
    setMessages(prev => [...prev, userMessage])

    handleStreamingResponse(message)
  }

  const handleStopGeneration = () => {
    if (abortController) {
      abortController.abort()
      setIsStreaming(false)
      setCurrentStreamingMessage('')
      setAbortController(null)
      
      setMessages(prev => 
        prev.map(msg => 
          msg.isStreaming 
            ? { ...msg, message: msg.message + '\n\nGeneration cancelled by user.', isStreaming: false }
            : msg
        )
      )
    }
  }

  return (
    <div className="max-w-6xl mx-auto">
      <div className="card">
        <div className="mb-6">
          <h1 className="text-2xl tiktok-sans-bold text-gray-900 mb-2">
            Crypto News Q&A
          </h1>
          <p className="text-gray-600 tiktok-sans-regular">
            Ask questions about cryptocurrency news and get real-time answers with live updates.
          </p>
        </div>

        {/* Messages */}
        <div className="mb-6 h-[600px] overflow-y-auto border border-gray-200 rounded-lg p-4 bg-gray-50">
          {messages.length === 0 ? (
            <div className="text-center text-gray-500 py-8">
              <p>Start by asking a question about crypto news!</p>
              <p className="text-sm mt-2">
                Try: "Is there any news about Bitcoin today?" or "What are the newest announcements on crypto ICOs?"
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {messages.map((msg) => (
                <ChatMessage
                  key={msg.id}
                  message={msg.message}
                  isUser={msg.isUser}
                  timestamp={msg.timestamp}
                  sources={msg.sources}
                  isStreaming={msg.isStreaming}
                />
              ))}
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="space-y-4">
          <ChatInput
            onSendMessage={handleSendMessage}
            isLoading={isStreaming}
            disabled={isStreaming}
          />
          
          {isStreaming && (
            <div className="flex items-center justify-center space-x-2">
              <div className="w-2 h-2 bg-primary-500 rounded-full animate-pulse"></div>
              <div className="w-2 h-2 bg-primary-500 rounded-full animate-pulse delay-100"></div>
              <div className="w-2 h-2 bg-primary-500 rounded-full animate-pulse delay-200"></div>
              <span className="text-sm text-gray-600">Generating answer...</span>
              <button
                onClick={handleStopGeneration}
                className="text-sm text-red-600 hover:text-red-700 font-medium"
              >
                Stop
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default ChatPage 