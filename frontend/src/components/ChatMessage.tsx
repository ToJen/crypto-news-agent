import { ExternalLink, Clock, Loader2 } from 'lucide-react'
import { NewsArticle } from '@/apis/cryptoNewsAPI'

interface ChatMessageProps {
  message: string
  isUser: boolean
  timestamp: string
  sources?: NewsArticle[]
  isStreaming?: boolean
}

const ChatMessage = ({ message, isUser, timestamp, sources, isStreaming = false }: ChatMessageProps) => {
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-6`}>
      <div className={`max-w-4xl ${isUser ? 'order-2' : 'order-1'}`}>
        <div
          className={`rounded-lg px-4 py-3 ${
            isUser
              ? 'bg-primary-500 text-white'
              : 'bg-white border border-gray-200 text-gray-900'
          }`}
        >
          {!isUser && isStreaming && !message && (
            <div className="flex items-center space-x-2 text-gray-500">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span className="text-sm">Generating answer...</span>
            </div>
          )}
          <div className="whitespace-pre-wrap tiktok-sans-regular">{message}</div>
          
          {!isUser && sources && sources.length > 0 && (
            <div className="mt-4 pt-3 border-t border-gray-200">
              <div className="text-sm text-gray-600 mb-2 tiktok-sans-medium">Sources:</div>
              <div className="space-y-2">
                {sources.map((source, index) => (
                  <div key={index} className="flex items-start space-x-2">
                    <div className="flex-1">
                      <div className="text-sm tiktok-sans-medium text-gray-900">
                        {source.title}
                      </div>
                      <div className="text-xs text-gray-500 flex items-center space-x-2">
                        <span>{source.source}</span>
                        <span>•</span>
                        <span className="flex items-center space-x-1">
                          <Clock size={12} />
                          <span>{new Date(source.published_at).toLocaleDateString()}</span>
                        </span>
                      </div>
                    </div>
                    {source.url && (
                      <a
                        href={source.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary-500 hover:text-primary-600"
                      >
                        <ExternalLink size={16} />
                      </a>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
        
        <div className={`text-xs text-gray-500 mt-1 ${isUser ? 'text-right' : 'text-left'}`}>
          {new Date(timestamp).toLocaleTimeString()}
        </div>
      </div>
    </div>
  )
}

export default ChatMessage 