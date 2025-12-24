import { useState, useRef, useEffect } from 'react'
import axios from 'axios'
import './ChatPanel.css'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function ChatPanel({ onNewAnswer, setIsLoading }) {
  const [messages, setMessages] = useState([])
  const [inputValue, setInputValue] = useState('')
  const [examples, setExamples] = useState([])
  const messagesEndRef = useRef(null)

  useEffect(() => {
    // Load example questions
    axios.get(`${API_URL}/examples`)
      .then(response => setExamples(response.data.examples))
      .catch(err => console.error('Failed to load examples:', err))

    // Add welcome message
    setMessages([{
      type: 'system',
      content: 'Welcome! Ask me anything about your CMDB infrastructure.'
    }])
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSubmit = async (question) => {
    if (!question.trim()) return

    const userMessage = {
      type: 'user',
      content: question
    }

    setMessages(prev => [...prev, userMessage])
    setInputValue('')
    setIsLoading(true)

    try {
      const response = await axios.post(`${API_URL}/ask`, {
        question: question
      })

      const answerData = response.data

      const assistantMessage = {
        type: 'assistant',
        content: answerData.answer,
        sources: answerData.sources
      }

      setMessages(prev => [...prev, assistantMessage])
      onNewAnswer(answerData)

    } catch (error) {
      console.error('Error:', error)
      const errorMessage = {
        type: 'error',
        content: error.response?.data?.detail || 'Failed to get answer. Please try again.'
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleExampleClick = (example) => {
    handleSubmit(example)
  }

  return (
    <div className="chat-panel">
      <div className="messages-container">
        {messages.map((message, index) => (
          <div key={index} className={`message ${message.type}`}>
            <div className="message-content">
              {message.content}
            </div>
            {message.sources && message.sources.length > 0 && (
              <div className="message-sources">
                <strong>Sources:</strong>
                <ul>
                  {message.sources.map((source, idx) => (
                    <li key={idx}>
                      {source.type}: {source.name}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {examples.length > 0 && messages.length === 1 && (
        <div className="examples-section">
          <p className="examples-title">Try these examples:</p>
          <div className="examples-grid">
            {examples.slice(0, 4).map((example, index) => (
              <button
                key={index}
                className="example-button"
                onClick={() => handleExampleClick(example)}
              >
                {example}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="input-container">
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyPress={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              handleSubmit(inputValue)
            }
          }}
          placeholder="Ask a question about your CMDB..."
          className="chat-input"
        />
        <button
          onClick={() => handleSubmit(inputValue)}
          className="send-button"
          disabled={!inputValue.trim()}
        >
          Send
        </button>
      </div>
    </div>
  )
}

export default ChatPanel
