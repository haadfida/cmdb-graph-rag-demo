import { useEffect, useRef } from 'react'
import { Network } from 'vis-network/standalone'
import './GraphVisualization.css'

function GraphVisualization({ graphData, isLoading }) {
  const containerRef = useRef(null)
  const networkRef = useRef(null)

  useEffect(() => {
    if (!graphData || !containerRef.current) {
      return
    }

    const { nodes, relationships } = graphData

    if (!nodes || nodes.length === 0) {
      return
    }

    // Color mapping for different node types
    const colorMap = {
      'Asset': '#4CAF50',
      'Service': '#2196F3',
      'User': '#FF9800',
      'Location': '#9C27B0',
      'Node': '#757575'
    }

    // Shape mapping for different node types
    const shapeMap = {
      'Asset': 'box',
      'Service': 'ellipse',
      'User': 'circle',
      'Location': 'diamond',
      'Node': 'dot'
    }

    // Transform nodes for vis-network
    const visNodes = nodes.map(node => {
      const label = node.labels.find(l => l !== 'Node') || 'Node'
      const color = colorMap[label] || colorMap['Node']
      const shape = shapeMap[label] || shapeMap['Node']
      const name = node.properties.name || 'Unknown'

      return {
        id: node.id,
        label: name,
        title: formatNodeTooltip(node),
        color: {
          background: color,
          border: darkenColor(color),
          highlight: {
            background: color,
            border: darkenColor(color)
          }
        },
        shape: shape,
        font: {
          color: '#ffffff',
          size: 14,
          face: 'Arial'
        },
        borderWidth: 2,
        borderWidthSelected: 3
      }
    })

    // Transform edges for vis-network
    const visEdges = relationships.map((rel, idx) => ({
      id: idx,
      from: rel.source,
      to: rel.target,
      label: rel.type,
      arrows: 'to',
      color: {
        color: '#848484',
        highlight: '#333333'
      },
      font: {
        size: 11,
        align: 'middle',
        background: 'rgba(255, 255, 255, 0.8)'
      },
      smooth: {
        type: 'curvedCW',
        roundness: 0.2
      }
    }))

    const data = {
      nodes: visNodes,
      edges: visEdges
    }

    const options = {
      nodes: {
        shadow: true
      },
      edges: {
        shadow: true,
        smooth: {
          type: 'continuous'
        }
      },
      physics: {
        enabled: true,
        solver: 'forceAtlas2Based',
        forceAtlas2Based: {
          gravitationalConstant: -50,
          centralGravity: 0.01,
          springLength: 150,
          springConstant: 0.08,
          damping: 0.4,
          avoidOverlap: 1
        },
        stabilization: {
          iterations: 150
        }
      },
      interaction: {
        hover: true,
        tooltipDelay: 200,
        zoomView: true,
        dragView: true
      },
      layout: {
        improvedLayout: true
      }
    }

    // Create or update network
    if (networkRef.current) {
      networkRef.current.setData(data)
    } else {
      networkRef.current = new Network(containerRef.current, data, options)

      // Add click event to show node details
      networkRef.current.on('click', (params) => {
        if (params.nodes.length > 0) {
          const nodeId = params.nodes[0]
          const node = nodes.find(n => n.id === nodeId)
          if (node) {
            console.log('Clicked node:', node)
          }
        }
      })
    }

    return () => {
      if (networkRef.current) {
        networkRef.current.destroy()
        networkRef.current = null
      }
    }
  }, [graphData])

  function formatNodeTooltip(node) {
    const label = node.labels.find(l => l !== 'Node') || 'Node'
    const props = node.properties
    const lines = [`<b>${label}</b>`]

    for (const [key, value] of Object.entries(props)) {
      if (key !== 'embedding' && key !== 'description') {
        lines.push(`${key}: ${value}`)
      }
    }

    return lines.join('<br/>')
  }

  function darkenColor(color) {
    // Simple color darkening function
    const hex = color.replace('#', '')
    const r = Math.max(0, parseInt(hex.substr(0, 2), 16) - 30)
    const g = Math.max(0, parseInt(hex.substr(2, 2), 16) - 30)
    const b = Math.max(0, parseInt(hex.substr(4, 2), 16) - 30)
    return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`
  }

  return (
    <div className="graph-visualization">
      {isLoading && (
        <div className="loading-overlay">
          <div className="loading-spinner"></div>
          <p>Loading graph...</p>
        </div>
      )}

      {!graphData && !isLoading && (
        <div className="empty-state">
          <div className="empty-icon">🔍</div>
          <h3>No graph data yet</h3>
          <p>Ask a question to see the relevant knowledge graph</p>
        </div>
      )}

      <div
        ref={containerRef}
        className="network-container"
        style={{ display: graphData ? 'block' : 'none' }}
      />

      {graphData && (
        <div className="graph-legend">
          <h4>Legend</h4>
          <div className="legend-items">
            <div className="legend-item">
              <span className="legend-color" style={{ background: '#4CAF50' }}></span>
              Asset
            </div>
            <div className="legend-item">
              <span className="legend-color" style={{ background: '#2196F3' }}></span>
              Service
            </div>
            <div className="legend-item">
              <span className="legend-color" style={{ background: '#FF9800' }}></span>
              User
            </div>
            <div className="legend-item">
              <span className="legend-color" style={{ background: '#9C27B0' }}></span>
              Location
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default GraphVisualization
