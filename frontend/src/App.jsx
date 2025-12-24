import { useState } from 'react'
import ChatPanel from './components/ChatPanel'
import GraphVisualization from './components/GraphVisualization'
import './App.css'

function App() {
  const [graphData, setGraphData] = useState(null)
  const [isLoading, setIsLoading] = useState(false)

  const handleNewAnswer = (answerData) => {
    if (answerData.graph_data) {
      setGraphData(answerData.graph_data)
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>🔍 CMDB Graph RAG Demo</h1>
        <p>Ask questions about your IT infrastructure</p>
      </header>

      <div className="app-content">
        <div className="left-panel">
          <ChatPanel
            onNewAnswer={handleNewAnswer}
            setIsLoading={setIsLoading}
          />
        </div>

        <div className="right-panel">
          <div className="graph-container">
            <h2>Knowledge Graph</h2>
            <GraphVisualization
              graphData={graphData}
              isLoading={isLoading}
            />
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
