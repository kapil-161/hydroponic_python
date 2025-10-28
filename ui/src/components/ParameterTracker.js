import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './ParameterTracker.css';

const ParameterTracker = () => {
  const [activeTab, setActiveTab] = useState('trace');
  const [selectedParameter, setSelectedParameter] = useState(null);
  const [traceData, setTraceData] = useState(null);
  const [impactData, setImpactData] = useState(null);
  const [summary, setSummary] = useState(null);
  const [searchResults, setSearchResults] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [allParameters, setAllParameters] = useState([]);
  const [flowData, setFlowData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showSearchResults, setShowSearchResults] = useState(false);

  useEffect(() => {
    fetchSummary();
    fetchAllParameters();
  }, []);

  const fetchSummary = async () => {
    try {
      const response = await axios.get('http://localhost:5001/api/parameter-tracking/summary');
      setSummary(response.data);
    } catch (err) {
      setError('Failed to load summary: ' + err.message);
    }
  };

  const fetchAllParameters = async () => {
    try {
      const response = await axios.get('http://localhost:5001/api/parameter-tracking/search?q=');
      setAllParameters(response.data.results);
    } catch (err) {
      console.error('Error fetching all parameters:', err);
    }
  };

  const handleParameterSearch = async (e) => {
    const query = e.target.value;
    setSearchQuery(query);
    setShowSearchResults(true);

    if (query.length === 0) {
      // Show all parameters when search is empty
      setSearchResults(allParameters);
      return;
    }

    if (query.length < 2) {
      setSearchResults([]);
      return;
    }

    try {
      const response = await axios.get(`http://localhost:5001/api/parameter-tracking/search?q=${query}`);
      setSearchResults(response.data.results);
    } catch (err) {
      console.error('Search error:', err);
    }
  };

  const handleSearchFocus = () => {
    setShowSearchResults(true);
    if (searchQuery.length === 0) {
      setSearchResults(allParameters);
    }
  };

  const handleSearchBlur = () => {
    // Delay hiding to allow click on results
    setTimeout(() => {
      setShowSearchResults(false);
    }, 200);
  };

  const handleSelectParameter = async (paramName) => {
    setSelectedParameter(paramName);
    setLoading(true);
    setError(null);

    try {
      const [traceRes, impactRes] = await Promise.all([
        axios.get(`http://localhost:5001/api/parameter-tracking/trace/${paramName}`),
        axios.get(`http://localhost:5001/api/parameter-tracking/impact/${paramName}`)
      ]);

      setTraceData(traceRes.data);
      setImpactData(impactRes.data);
      setSearchResults([]);
      setSearchQuery('');
    } catch (err) {
      setError('Failed to load parameter data: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleViewFlow = async () => {
    try {
      const response = await axios.get('http://localhost:5001/api/parameter-tracking/flow');
      setFlowData(response.data);
      setActiveTab('flow');
    } catch (err) {
      setError('Failed to load flow data: ' + err.message);
    }
  };

  return (
    <div className="parameter-tracker">
      <div className="tracker-header">
        <h2>🔍 Parameter Tracker</h2>
        <p>Trace where each parameter is used, how it's used, and what it yields</p>
      </div>

      <div className="tracker-nav">
        <button
          className={`nav-btn ${activeTab === 'trace' ? 'active' : ''}`}
          onClick={() => setActiveTab('trace')}
        >
          Parameter Trace
        </button>
        <button
          className={`nav-btn ${activeTab === 'impact' ? 'active' : ''}`}
          onClick={() => setActiveTab('impact')}
        >
          Impact Analysis
        </button>
        <button
          className={`nav-btn ${activeTab === 'flow' ? 'active' : ''}`}
          onClick={() => {
            handleViewFlow();
          }}
        >
          Parameter Flow
        </button>
        <button
          className={`nav-btn ${activeTab === 'summary' ? 'active' : ''}`}
          onClick={() => setActiveTab('summary')}
        >
          Summary
        </button>
      </div>

      {error && <div className="error-message">{error}</div>}

      <div className="tracker-content">
        {/* Trace Tab */}
        {activeTab === 'trace' && (
          <div className="trace-section">
            <div className="search-container">
              <input
                type="text"
                placeholder="Search parameters (e.g., base_temperature, leaf_area)..."
                value={searchQuery}
                onChange={handleParameterSearch}
                onFocus={handleSearchFocus}
                onBlur={handleSearchBlur}
                className="search-input"
              />
              {showSearchResults && searchResults.length > 0 && (
                <div className="search-results">
                  {searchResults.map((result) => (
                    <div
                      key={result.name}
                      className="search-result-item"
                      onClick={() => handleSelectParameter(result.name)}
                    >
                      <div className="result-name">{result.name}</div>
                      <div className="result-meta">
                        <span className="file-badge">{result.file}</span>
                        <span className="count-badge">{result.usage_count} models</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {selectedParameter && loading && (
              <div className="loading">Loading parameter trace...</div>
            )}

            {selectedParameter && traceData && !loading && (
              <div className="trace-data">
                <div className="parameter-header">
                  <h3>{selectedParameter}</h3>
                  <button
                    className="btn-close"
                    onClick={() => {
                      setSelectedParameter(null);
                      setTraceData(null);
                      setImpactData(null);
                    }}
                  >
                    ✕
                  </button>
                </div>

                <div className="trace-grid">
                  {/* Source */}
                  <div className="trace-card">
                    <h4>📁 Source</h4>
                    <div className="card-content">
                      <div className="info-row">
                        <span className="label">File:</span>
                        <span className="value">{traceData.source.file}</span>
                      </div>
                      <div className="info-row">
                        <span className="label">Current Value:</span>
                        <span className="value">{traceData.source.value}</span>
                      </div>
                      <div className="info-row">
                        <span className="label">Unit:</span>
                        <span className="value">{traceData.source.unit || 'N/A'}</span>
                      </div>
                      <div className="info-row">
                        <span className="label">Description:</span>
                        <span className="value">{traceData.source.description}</span>
                      </div>
                    </div>
                  </div>

                  {/* Used By */}
                  <div className="trace-card">
                    <h4>🔗 Used By Models</h4>
                    <div className="card-content">
                      {traceData.used_by_models.length > 0 ? (
                        <div className="tags">
                          {traceData.used_by_models.map((model) => (
                            <span key={model} className="model-tag">
                              {model}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <p className="no-data">Not used by any models</p>
                      )}
                    </div>
                  </div>

                  {/* Produces */}
                  <div className="trace-card">
                    <h4>📤 Produces Outputs</h4>
                    <div className="card-content">
                      {traceData.produces.length > 0 ? (
                        <div className="tags">
                          {traceData.produces.map((output, idx) => (
                            <span key={idx} className="output-tag">
                              {output.outputs ? output.outputs.join(', ') : output}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <p className="no-data">No direct outputs</p>
                      )}
                    </div>
                  </div>

                  {/* Equations */}
                  <div className="trace-card">
                    <h4>⚙️ Usage in Code</h4>
                    <div className="card-content">
                      {traceData.equations.length > 0 ? (
                        <div className="equations">
                          {traceData.equations.map((eq, idx) => (
                            <div key={idx} className="equation-item">
                              <div className="equation-header">
                                {eq.model} : Line {eq.line}
                              </div>
                              <div className="equation-code">{eq.code}</div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="no-data">No usage details found</p>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Impact Tab */}
        {activeTab === 'impact' && selectedParameter && impactData && (
          <div className="impact-section">
            <div className="impact-grid">
              <div className="impact-card">
                <h4>📊 Parameter Info</h4>
                <div className="card-content">
                  <div className="info-row">
                    <span className="label">Parameter:</span>
                    <span className="value">{impactData.parameter}</span>
                  </div>
                  <div className="info-row">
                    <span className="label">CSV Source:</span>
                    <span className="value">{impactData.csv_source}</span>
                  </div>
                  <div className="info-row">
                    <span className="label">Current Value:</span>
                    <span className="value">{impactData.current_value} {impactData.unit}</span>
                  </div>
                  <div className="info-row">
                    <span className="label">Sensitivity:</span>
                    <span className={`sensitivity-badge ${impactData.estimated_sensitivity}`}>
                      {impactData.estimated_sensitivity.toUpperCase()}
                    </span>
                  </div>
                </div>
              </div>

              <div className="impact-card">
                <h4>🎯 Direct Impact</h4>
                <div className="card-content">
                  <div className="info-row">
                    <span className="label">Models Affected:</span>
                    <span className="value">{impactData.direct_impact.model_count}</span>
                  </div>
                  <div className="tags">
                    {impactData.direct_impact.models_using.map((model) => (
                      <span key={model} className="model-tag">
                        {model}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              <div className="impact-card">
                <h4>📈 Affected Outputs</h4>
                <div className="card-content">
                  {impactData.affected_outputs.length > 0 ? (
                    <div className="tags">
                      {impactData.affected_outputs.map((output) => (
                        <span key={output} className="output-tag">
                          {output}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <p className="no-data">No outputs affected</p>
                  )}
                </div>
              </div>

              <div className="impact-card">
                <h4>⚡ Execution Flow</h4>
                <div className="card-content">
                  {impactData.execution_flow.length > 0 ? (
                    <div className="flow-list">
                      {impactData.execution_flow.map((model, idx) => (
                        <div key={model} className="flow-item">
                          <span className="flow-number">{idx + 1}</span>
                          <span className="flow-model">{model}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="no-data">No execution flow</p>
                  )}
                </div>
              </div>

              <div className="impact-card">
                <h4>🔗 Related Parameters</h4>
                <div className="card-content">
                  {impactData.relationships && Object.keys(impactData.relationships).length > 0 ? (
                    Object.entries(impactData.relationships).map(([model, params]) => (
                      <div key={model} className="relationship-group">
                        <div className="relationship-model">{model}</div>
                        <div className="tags">
                          {params.map((param) => (
                            <span
                              key={param}
                              className="param-tag"
                              onClick={() => handleSelectParameter(param)}
                            >
                              {param}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))
                  ) : (
                    <p className="no-data">No related parameters</p>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Flow Tab */}
        {activeTab === 'flow' && flowData && (
          <div className="flow-section">
            <div className="flow-visualization">
              <p className="flow-count">Showing {Object.keys(flowData).length} parameter flows</p>
              {Object.entries(flowData)
                .map(([param, flow]) => (
                  <div key={param} className="flow-item-card">
                    <div className="flow-element input">
                      <div className="element-label">📁</div>
                      <div className="element-name">{flow.source_file}</div>
                    </div>

                    <div className="flow-arrow">→</div>

                    <div className="flow-element parameter">
                      <div className="element-label">🔧</div>
                      <div className="element-name">{param}</div>
                      <div className="element-value">{flow.value}</div>
                    </div>

                    <div className="flow-arrow">→</div>

                    <div className="flow-element models">
                      {flow.models && flow.models.length > 0 ? (
                        <>
                          <div className="element-label">⚙️</div>
                          {flow.models.map((model) => (
                            <div key={model} className="element-name small">
                              {model}
                            </div>
                          ))}
                        </>
                      ) : (
                        <div className="element-name">No models</div>
                      )}
                    </div>

                    <div className="flow-arrow">→</div>

                    <div className="flow-element outputs">
                      {flow.outputs && flow.outputs.length > 0 ? (
                        <>
                          <div className="element-label">📤</div>
                          {flow.outputs.map((output) => (
                            <div key={output} className="element-name small">
                              {output}
                            </div>
                          ))}
                        </>
                      ) : (
                        <div className="element-name">No outputs</div>
                      )}
                    </div>
                  </div>
                ))}
            </div>
            {Object.keys(flowData).length > 20 && (
              <p className="note">
                Showing first 20 parameters. Total: {Object.keys(flowData).length}
              </p>
            )}
          </div>
        )}

        {/* Summary Tab */}
        {activeTab === 'summary' && summary && (
          <div className="summary-section">
            <div className="summary-grid">
              <div className="summary-card large">
                <div className="summary-value">{summary.total_parameters}</div>
                <div className="summary-label">Total Parameters</div>
              </div>

              <div className="summary-card large">
                <div className="summary-value">{summary.used_parameters}</div>
                <div className="summary-label">Used Parameters</div>
              </div>

              <div className="summary-card large">
                <div className="summary-value">{summary.unused_parameters}</div>
                <div className="summary-label">Unused Parameters</div>
              </div>

              <div className="summary-card large">
                <div className="summary-value">{summary.total_models}</div>
                <div className="summary-label">Models</div>
              </div>
            </div>

            {summary.unused_parameters > 0 && summary.unused_params_detail && (
              <div className="unused-parameters-section">
                <h4>⚠️ Unused Parameters ({summary.unused_parameters})</h4>
                <p className="note">These parameters are defined but not used by any model:</p>

                {summary.unused_by_file && Object.keys(summary.unused_by_file).length > 0 ? (
                  <div className="unused-by-file">
                    {Object.entries(summary.unused_by_file).map(([file, params]) => (
                      <div key={file} className="file-group">
                        <div className="file-header">📄 {file}</div>
                        <div className="unused-list">
                          {params.map((param) => (
                            <div
                              key={param.name}
                              className="unused-item"
                              onClick={() => handleSelectParameter(param.name)}
                            >
                              <div className="param-name">{param.name}</div>
                              <div className="param-meta">
                                <span className="param-value">Value: {param.value}</span>
                                {param.unit && <span className="param-unit">Unit: {param.unit}</span>}
                                {param.description && <span className="param-desc">{param.description}</span>}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="unused-list">
                    {summary.unused_params_detail.map((param) => (
                      <div
                        key={param.name}
                        className="unused-item"
                        onClick={() => handleSelectParameter(param.name)}
                      >
                        <div className="param-name">{param.name}</div>
                        <div className="param-meta">
                          <span className="file-badge">{param.file}</span>
                          <span className="param-value">{param.value}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            <div className="models-section">
              <h4>📊 Models</h4>
              <div className="models-grid">
                {summary.models && summary.models.map((model) => (
                  <div key={model} className="model-card">
                    <div className="model-name">{model}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ParameterTracker;
