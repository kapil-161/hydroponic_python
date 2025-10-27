import React, { useEffect, useState, useRef } from 'react';
import axios from 'axios';
import './ModelGraph.css';

const ModelGraph = () => {
  const [graph, setGraph] = useState(null);
  const [selectedModel, setSelectedModel] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [layout, setLayout] = useState('hierarchical');
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [showDepth, setShowDepth] = useState(true);
  const [showConnections, setShowConnections] = useState(true);
  const [hoveredEdge, setHoveredEdge] = useState(null);
  const [nodePositions, setNodePositions] = useState({});
  const [draggedNode, setDraggedNode] = useState(null);
  const [selectedEdges, setSelectedEdges] = useState(new Set());
  const svgRef = useRef(null);

  useEffect(() => {
    fetchGraph();
  }, []);

  const fetchGraph = async () => {
    try {
      setLoading(true);
      const response = await axios.get('http://localhost:5001/api/graph');
      setGraph(response.data);
      setError(null);
    } catch (err) {
      setError('Failed to load model graph: ' + err.message);
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const layoutNodes = (nodes, layoutType) => {
    switch (layoutType) {
      case 'circular':
        return layoutCircular(nodes);
      case 'force-directed':
        return layoutForceDirected(nodes);
      case 'hierarchical':
      default:
        return layoutHierarchical(nodes);
    }
  };

  const layoutHierarchical = (nodes) => {
    const categories = {};
    nodes.forEach((node) => {
      if (!categories[node.category]) {
        categories[node.category] = [];
      }
      categories[node.category].push(node);
    });

    let yPos = 50;
    const layoutedNodes = [];

    Object.entries(categories).forEach(([category, categoryNodes]) => {
      let xPos = 50;
      categoryNodes.forEach((node) => {
        layoutedNodes.push({
          ...node,
          x: xPos,
          y: yPos,
        });
        xPos += 320;
      });
      yPos += 320;
    });

    return layoutedNodes;
  };

  const layoutCircular = (nodes) => {
    const radius = 300;
    const angle = (2 * Math.PI) / nodes.length;
    const centerX = 500;
    const centerY = 400;

    return nodes.map((node, idx) => ({
      ...node,
      x: centerX + radius * Math.cos(angle * idx),
      y: centerY + radius * Math.sin(angle * idx),
    }));
  };

  const layoutForceDirected = (nodes) => {
    // Simple force-directed layout (basic spring model)
    const layouted = nodes.map((node, idx) => ({
      ...node,
      x: Math.random() * 800,
      y: Math.random() * 600,
    }));
    return layouted;
  };

  const handleZoom = (direction) => {
    setZoom((prev) => {
      const newZoom = direction === 'in' ? prev + 0.15 : prev - 0.15;
      return Math.max(0.2, Math.min(3, newZoom));
    });
  };

  const handleNodeMouseDown = (e, nodeId) => {
    e.stopPropagation();
    if (e.button === 0) {
      // Left mouse button for node dragging
      setDraggedNode(nodeId);
      setDragStart({ x: e.clientX, y: e.clientY });
    }
  };

  const handleMouseDown = (e) => {
    if (e.button === 2) {
      // Right mouse button for canvas panning
      setIsDragging(true);
      setDragStart({ x: e.clientX, y: e.clientY });
    }
  };

  const handleMouseMove = (e) => {
    if (draggedNode) {
      // Node dragging
      const dx = e.clientX - dragStart.x;
      const dy = e.clientY - dragStart.y;
      setNodePositions((prev) => ({
        ...prev,
        [draggedNode]: {
          x: (prev[draggedNode]?.x || 0) + dx / zoom,
          y: (prev[draggedNode]?.y || 0) + dy / zoom,
        },
      }));
      setDragStart({ x: e.clientX, y: e.clientY });
    } else if (isDragging) {
      // Canvas panning
      const dx = e.clientX - dragStart.x;
      const dy = e.clientY - dragStart.y;
      setPan((prev) => ({
        x: prev.x + dx,
        y: prev.y + dy,
      }));
      setDragStart({ x: e.clientX, y: e.clientY });
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
    setDraggedNode(null);
  };

  const resetView = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };

  const toggleEdgeSelection = (edgeIdx) => {
    setSelectedEdges((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(edgeIdx)) {
        newSet.delete(edgeIdx);
      } else {
        newSet.add(edgeIdx);
      }
      return newSet;
    });
  };

  const clearEdgeSelection = () => {
    setSelectedEdges(new Set());
  };

  const exportGraph = () => {
    if (svgRef.current) {
      const svg = svgRef.current;
      const svgData = new XMLSerializer().serializeToString(svg);
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      const img = new Image();
      img.onload = () => {
        ctx.drawImage(img, 0, 0);
        const link = document.createElement('a');
        link.href = canvas.toDataURL('image/png');
        link.download = 'model-graph.png';
        link.click();
      };
      img.src = 'data:image/svg+xml;base64,' + btoa(svgData);
    }
  };

  if (loading) {
    return <div className="loading">Loading model graph...</div>;
  }

  if (error) {
    return <div className="error">{error}</div>;
  }

  if (!graph) {
    return <div className="loading">No graph data available</div>;
  }

  const layoutedNodes = layoutNodes(graph.nodes, layout);

  // Filter nodes based on search and category
  const filteredNodes = layoutedNodes.filter((node) => {
    const matchesSearch = node.label.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = !selectedCategory || node.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  const getNodesByCategory = () => {
    const categories = {};
    layoutedNodes.forEach((node) => {
      if (!categories[node.category]) {
        categories[node.category] = [];
      }
      categories[node.category].push(node);
    });
    return categories;
  };

  const categories = getNodesByCategory();

  return (
    <div className="model-graph">
      <div className="graph-controls">
        <div className="control-section">
          <label>Layout:</label>
          <select value={layout} onChange={(e) => setLayout(e.target.value)}>
            <option value="hierarchical">Hierarchical</option>
            <option value="circular">Circular</option>
            <option value="force-directed">Force-Directed</option>
          </select>
        </div>

        <div className="control-section">
          <label>Filter by Category:</label>
          <select
            value={selectedCategory || ''}
            onChange={(e) => setSelectedCategory(e.target.value || null)}
          >
            <option value="">All Categories</option>
            {Object.keys(categories).map((cat) => (
              <option key={cat} value={cat}>
                {cat}
              </option>
            ))}
          </select>
        </div>

        <div className="control-section">
          <label>Search Models:</label>
          <input
            type="text"
            placeholder="Search by name..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="search-input"
          />
        </div>

        <div className="control-section">
          <button onClick={() => handleZoom('in')} className="btn-small">
            🔍+ Zoom In
          </button>
          <button onClick={() => handleZoom('out')} className="btn-small">
            🔍- Zoom Out
          </button>
          <button onClick={resetView} className="btn-small">
            🎯 Reset
          </button>
          <button onClick={exportGraph} className="btn-small">
            📥 Export
          </button>
        </div>

        <div className="control-section">
          <label>
            <input
              type="checkbox"
              checked={showDepth}
              onChange={(e) => setShowDepth(e.target.checked)}
            />
            📊 Show Depth
          </label>
          <label>
            <input
              type="checkbox"
              checked={showConnections}
              onChange={(e) => setShowConnections(e.target.checked)}
            />
            🔗 Connection Strength
          </label>
          {selectedEdges.size > 0 && (
            <button onClick={clearEdgeSelection} className="btn-small">
              ✕ Clear Selection ({selectedEdges.size})
            </button>
          )}
        </div>

        <div className="graph-stats">
          <span>Models: {filteredNodes.length} / {layoutedNodes.length}</span>
          <span>Connections: {graph.edges.length}</span>
          <span>Categories: {Object.keys(categories).length}</span>
          {graph.summary && (
            <>
              <span>Max Depth: {graph.summary.max_depth}</span>
              <span>Input Models: {graph.summary.input_models}</span>
              <span>Output Models: {graph.summary.output_models}</span>
            </>
          )}
        </div>
      </div>

      <div
        className="graph-container"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onContextMenu={(e) => e.preventDefault()}
      >
        <svg
          ref={svgRef}
          className="graph-svg"
          viewBox={`0 0 ${Math.max(1200, layoutedNodes.length * 300)} ${Math.max(800, Object.keys(categories).length * 320)}`}
          style={{
            transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
            transformOrigin: '0 0',
            cursor: isDragging ? 'grabbing' : 'grab',
            width: '100%',
            height: '100%',
            minWidth: '100%',
            minHeight: '100%',
          }}
        >
          <defs>
            <marker
              id="arrowhead"
              markerWidth="10"
              markerHeight="10"
              refX="9"
              refY="3"
              orient="auto"
            >
              <polygon points="0 0, 10 3, 0 6" fill="#666" />
            </marker>
          </defs>

          {/* Draw edges */}
          {graph.edges.map((edge, idx) => {
            const sourceNode = layoutedNodes.find((n) => n.id === edge.source);
            const targetNode = layoutedNodes.find((n) => n.id === edge.target);

            if (!sourceNode || !targetNode) return null;
            if (
              !filteredNodes.includes(sourceNode) ||
              !filteredNodes.includes(targetNode)
            )
              return null;

            // Use custom position if node was dragged, otherwise use layout position
            const sourceX = nodePositions[edge.source]?.x ?? sourceNode.x;
            const sourceY = nodePositions[edge.source]?.y ?? sourceNode.y;
            const targetX = nodePositions[edge.target]?.x ?? targetNode.x;
            const targetY = nodePositions[edge.target]?.y ?? targetNode.y;

            const x1 = sourceX + 100;
            const y1 = sourceY + 60;
            const x2 = targetX + 100;
            const y2 = targetY;

            // Calculate edge properties
            const strength = edge.strength || 0;
            const isMajor = edge.is_major;
            const strokeWidth = showConnections ? 1 + Math.min(strength / 3, 3) : 2;

            // Determine stroke color based on selection, hover state and connection type
            let strokeColor = '#666';
            let opacity = 1;
            let strokeWidth2 = strokeWidth;

            if (selectedEdges.has(idx)) {
              // Selected edges - bright green with thick stroke
              strokeColor = '#4CAF50';
              opacity = 1;
              strokeWidth2 = Math.max(strokeWidth + 2, 4);
            } else if (hoveredEdge === idx) {
              // Hovered edges - red
              strokeColor = '#FF6B6B';
              opacity = 1;
            } else if (isMajor) {
              // Major connections - blue
              strokeColor = '#2196F3';
              opacity = 0.85;
            }

            return (
              <g key={`edge-${idx}`}>
                <line
                  x1={x1}
                  y1={y1}
                  x2={x2}
                  y2={y2}
                  className="graph-edge"
                  style={{
                    strokeWidth: `${strokeWidth2}px`,
                    stroke: strokeColor,
                    opacity: opacity,
                    strokeDasharray: isMajor && !selectedEdges.has(idx) ? '5,5' : 'none',
                    transition: 'all 0.2s ease',
                    cursor: 'pointer'
                  }}
                  markerEnd="url(#arrowhead)"
                  onMouseEnter={() => setHoveredEdge(idx)}
                  onMouseLeave={() => setHoveredEdge(null)}
                  onClick={(e) => {
                    e.stopPropagation();
                    toggleEdgeSelection(idx);
                  }}
                />
                {showConnections && edge.parameter_count > 0 && (
                  <text
                    x={(x1 + x2) / 2}
                    y={(y1 + y2) / 2 - 5}
                    className="edge-label"
                    textAnchor="middle"
                  >
                    {edge.parameter_count}
                  </text>
                )}
              </g>
            );
          })}

          {/* Draw nodes */}
          {filteredNodes.map((node) => {
            // Use custom position if node was dragged, otherwise use layout position
            const x = nodePositions[node.id]?.x ?? node.x;
            const y = nodePositions[node.id]?.y ?? node.y;

            return (
            <g
              key={node.id}
              className="graph-node"
              transform={`translate(${x}, ${y})`}
              onClick={() => setSelectedModel(node.id)}
              onMouseDown={(e) => handleNodeMouseDown(e, node.id)}
              style={{
                cursor: draggedNode === node.id ? 'grabbing' : 'grab',
                userSelect: 'none'
              }}
            >
              <rect
                width="200"
                height="140"
                rx="8"
                fill={selectedModel === node.id ? node.color : '#fff'}
                stroke={node.color}
                strokeWidth={selectedModel === node.id ? 3 : 2}
                className="node-rect"
                opacity={selectedModel && selectedModel !== node.id ? 0.6 : 1}
              />
              <text
                x="100"
                y="35"
                textAnchor="middle"
                className="node-label"
                fill={selectedModel === node.id ? '#fff' : '#000'}
                fontWeight="bold"
              >
                {node.label}
              </text>
              <text
                x="100"
                y="65"
                textAnchor="middle"
                className="node-category"
                fill={selectedModel === node.id ? '#fff' : '#666'}
                fontSize="12"
              >
                {node.category}
              </text>
              <text
                x="100"
                y="95"
                textAnchor="middle"
                className="node-description"
                fill={selectedModel === node.id ? '#fff' : '#999'}
                fontSize="10"
              >
                <tspan x="100" dy="1.2em">
                  {node.description.substring(0, 25)}
                </tspan>
              </text>
              {showDepth && node.depth !== undefined && (
                <g>
                  <circle
                    cx="180"
                    cy="15"
                    r="12"
                    fill={node.is_input ? '#4caf50' : node.is_output ? '#ff9800' : '#2196f3'}
                    opacity="0.8"
                  />
                  <text
                    x="180"
                    y="20"
                    textAnchor="middle"
                    className="depth-label"
                    fill="white"
                    fontSize="11"
                    fontWeight="bold"
                  >
                    {node.depth}
                  </text>
                </g>
              )}
            </g>
            );
          })}
        </svg>
      </div>

      {selectedModel && (
        <div className="model-info-panel">
          <button
            className="close-btn"
            onClick={() => setSelectedModel(null)}
          >
            ✕
          </button>
          <h3>{layoutedNodes.find((n) => n.id === selectedModel)?.label}</h3>
          <p>
            <strong>Category:</strong>{' '}
            {layoutedNodes.find((n) => n.id === selectedModel)?.category}
          </p>
          <p>
            <strong>Description:</strong>{' '}
            {layoutedNodes.find((n) => n.id === selectedModel)?.description}
          </p>

          {/* Show connected models */}
          {graph.edges.filter((e) => e.source === selectedModel).length > 0 && (
            <div className="connected">
              <h4>↓ Outputs to:</h4>
              <ul>
                {graph.edges
                  .filter((e) => e.source === selectedModel)
                  .map((edge) => {
                    const targetLabel = layoutedNodes.find(
                      (n) => n.id === edge.target
                    )?.label;
                    return <li key={edge.target}>{targetLabel}</li>;
                  })}
              </ul>
            </div>
          )}

          {graph.edges.filter((e) => e.target === selectedModel).length > 0 && (
            <div className="connected">
              <h4>↑ Receives from:</h4>
              <ul>
                {graph.edges
                  .filter((e) => e.target === selectedModel)
                  .map((edge) => {
                    const sourceLabel = layoutedNodes.find(
                      (n) => n.id === edge.source
                    )?.label;
                    return <li key={edge.source}>{sourceLabel}</li>;
                  })}
              </ul>
            </div>
          )}

          <div className="model-stats">
            <p>
              <strong>Inputs:</strong>{' '}
              {graph.edges.filter((e) => e.target === selectedModel).length}
            </p>
            <p>
              <strong>Outputs:</strong>{' '}
              {graph.edges.filter((e) => e.source === selectedModel).length}
            </p>
          </div>
        </div>
      )}

      <div className="legend">
        <h4>Model Categories ({Object.keys(categories).length})</h4>
        {Object.entries(categories).map(([category, nodes]) => (
          <div
            key={category}
            className={`legend-item ${selectedCategory === category ? 'active' : ''}`}
            onClick={() =>
              setSelectedCategory(
                selectedCategory === category ? null : category
              )
            }
          >
            <div
              className="legend-color"
              style={{
                backgroundColor: nodes[0]?.color || '#ccc',
              }}
            ></div>
            <span>
              {category} ({nodes.length})
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ModelGraph;
