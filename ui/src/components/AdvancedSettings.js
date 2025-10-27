import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './AdvancedSettings.css';

const AdvancedSettings = () => {
  const [activeTab, setActiveTab] = useState('equations');
  const [models, setModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState(null);
  const [modelEquations, setModelEquations] = useState(null);
  const [modelConfig, setModelConfig] = useState(null);
  const [systemInfo, setSystemInfo] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [editingEquation, setEditingEquation] = useState(null);
  const [configEdits, setConfigEdits] = useState({});

  useEffect(() => {
    fetchSystemInfo();
  }, []);

  const fetchSystemInfo = async () => {
    try {
      const response = await axios.get('http://localhost:5001/api/advanced/system-info');
      setSystemInfo(response.data);

      // Get list of models from settings
      const settingsRes = await axios.get('http://localhost:5001/api/advanced/settings');
      const modelFiles = settingsRes.data.model_files.map(f =>
        f.split('/').pop().replace('.py', '')
      ).filter(name => name !== '__init__' && name !== 'base_model');

      setModels(modelFiles);
    } catch (err) {
      setError('Failed to load system info: ' + err.message);
    }
  };

  const handleSelectModel = async (modelName) => {
    setSelectedModel(modelName);
    setLoading(true);
    setError(null);

    try {
      // Map model names to CSV file names
      const csvNameMap = {
        'photosynthesis_model': 'photo',
        'respiration_model': 'respiration',
        'biomass_allocation_model': 'allocation',
        'root_system_model': 'roots',
        'water_uptake_model': 'water',
        'stress_models': 'stress',
        'nutrient_models': 'nutrient',
        'nitrogen_balance': 'nitrogen_balance',
        'canopy_architecture_model': 'canopy',
        'leaf_development_model': 'leaf',
        'canopy_architecture': 'canopy',
        'leaf_development': 'leaf',
        'phenology_model': 'phenology'
      };

      const csvName = csvNameMap[modelName] || modelName;

      // Load equations (required)
      const eqRes = await axios.get(`http://localhost:5001/api/advanced/equations/${modelName}`);
      setModelEquations(eqRes.data);

      // Load config (may not exist for all models)
      try {
        const configRes = await axios.get(`http://localhost:5001/api/advanced/configs/${csvName}`);
        setModelConfig(configRes.data);
      } catch (configErr) {
        // Config not found is OK, just set empty config
        if (configErr.response?.status === 404) {
          setModelConfig(null);
        } else {
          throw configErr;
        }
      }
    } catch (err) {
      setError('Failed to load model data: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleConfigChange = (paramName, newValue) => {
    setConfigEdits(prev => ({
      ...prev,
      [paramName]: newValue
    }));
  };

  const handleSaveConfig = async () => {
    try {
      const updates = Object.entries(configEdits).map(([name, value]) => ({
        parameter_name: name,
        value: value
      }));

      await axios.put(
        `http://localhost:5001/api/advanced/configs/${selectedModel}`,
        { parameters: updates }
      );

      setConfigEdits({});
      alert('Configuration saved!');
    } catch (err) {
      setError('Failed to save configuration: ' + err.message);
    }
  };

  return (
    <div className="advanced-settings">
      <div className="settings-header">
        <h2>⚙️ Advanced Settings & Control</h2>
        <p>Edit equations, configurations, and system settings</p>
      </div>

      <div className="settings-nav">
        <button
          className={`nav-btn ${activeTab === 'equations' ? 'active' : ''}`}
          onClick={() => setActiveTab('equations')}
        >
          Equations
        </button>
        <button
          className={`nav-btn ${activeTab === 'config' ? 'active' : ''}`}
          onClick={() => setActiveTab('config')}
        >
          Configuration
        </button>
        <button
          className={`nav-btn ${activeTab === 'system' ? 'active' : ''}`}
          onClick={() => setActiveTab('system')}
        >
          System Info
        </button>
      </div>

      {error && <div className="error-message">{error}</div>}

      <div className="settings-content">
        {/* Equations Tab */}
        {activeTab === 'equations' && (
          <div className="equations-section">
            <div className="models-sidebar">
              <h3>Models</h3>
              <div className="models-list">
                {models.map((model) => (
                  <button
                    key={model}
                    className={`model-btn ${selectedModel === model ? 'active' : ''}`}
                    onClick={() => handleSelectModel(model)}
                  >
                    {model}
                  </button>
                ))}
              </div>
            </div>

            <div className="equations-main">
              {selectedModel && loading && (
                <div className="loading">Loading equations...</div>
              )}

              {selectedModel && modelEquations && !loading && (
                <div className="equations-display">
                  <h3>{selectedModel}</h3>

                  {modelEquations.methods && modelEquations.methods.length > 0 && (
                    <div className="equations-card">
                      <h4>📋 Methods/Functions</h4>
                      {modelEquations.methods.map((method, idx) => (
                        <div key={idx} className="method-item">
                          <div className="method-header">
                            <span className="method-name">{method.name}</span>
                            <span className="method-line">Line {method.line}</span>
                          </div>
                          {method.docstring && (
                            <div className="method-doc">{method.docstring}</div>
                          )}
                          <div className="method-params">
                            <strong>Parameters:</strong> {method.params.join(', ')}
                          </div>
                          <button
                            className="btn-view-code"
                            onClick={() => setEditingEquation(method)}
                          >
                            View Code
                          </button>
                        </div>
                      ))}
                    </div>
                  )}

                  {modelEquations.calculations && modelEquations.calculations.length > 0 && (
                    <div className="equations-card">
                      <h4>🔢 Calculations ({modelEquations.calculations.length} total)</h4>
                      <div className="calculations-grid">
                        {modelEquations.calculations.map((calc, idx) => (
                          <div key={idx} className="calc-item">
                            <div className="calc-var">{calc.variable}</div>
                            <div className="calc-line">Line {calc.line}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {editingEquation && (
                    <div className="code-viewer">
                      <div className="viewer-header">
                        <h4>{editingEquation.name}</h4>
                        <button
                          className="btn-close"
                          onClick={() => setEditingEquation(null)}
                        >
                          ✕
                        </button>
                      </div>
                      <pre className="code-content">{editingEquation.code}</pre>
                      <div className="viewer-note">
                        ⚠️ Note: Direct code editing requires model reload. Changes are not applied immediately.
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Configuration Tab */}
        {activeTab === 'config' && (
          <div className="config-section">
            <div className="models-sidebar">
              <h3>Models</h3>
              <div className="models-list">
                {models.map((model) => (
                  <button
                    key={model}
                    className={`model-btn ${selectedModel === model ? 'active' : ''}`}
                    onClick={() => handleSelectModel(model)}
                  >
                    {model}
                  </button>
                ))}
              </div>
            </div>

            <div className="config-main">
              {selectedModel && loading && (
                <div className="loading">Loading configuration...</div>
              )}

              {selectedModel && !modelConfig && !loading && (
                <div className="config-display">
                  <div className="info-message">
                    ℹ️ No configuration file available for this model. (Base models or utility modules may not have parameters.)
                  </div>
                </div>
              )}

              {selectedModel && modelConfig && !loading && (
                <div className="config-display">
                  <div className="config-header">
                    <h3>{selectedModel} Configuration</h3>
                    {Object.keys(configEdits).length > 0 && (
                      <button
                        className="btn-save-config"
                        onClick={handleSaveConfig}
                      >
                        💾 Save Changes ({Object.keys(configEdits).length})
                      </button>
                    )}
                  </div>

                  <div className="config-params">
                    {modelConfig.data && modelConfig.data.map((param, idx) => {
                      const paramName = param.parameter_name;
                      const currentValue = configEdits[paramName] !== undefined
                        ? configEdits[paramName]
                        : param.value;
                      const isEdited = configEdits[paramName] !== undefined;

                      return (
                        <div
                          key={idx}
                          className={`config-param-card ${isEdited ? 'edited' : ''}`}
                        >
                          <div className="param-label">{paramName}</div>
                          <input
                            type="text"
                            value={currentValue}
                            onChange={(e) =>
                              handleConfigChange(paramName, e.target.value)
                            }
                            className="param-input"
                            placeholder="Enter value"
                          />
                          <div className="param-info">
                            {param.unit && <span className="unit">{param.unit}</span>}
                            {param.description && (
                              <span className="desc">{param.description}</span>
                            )}
                          </div>
                          {isEdited && (
                            <div className="param-original">
                              Original: {param.value}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* System Info Tab */}
        {activeTab === 'system' && systemInfo && (
          <div className="system-info-section">
            <div className="info-grid">
              <div className="info-card">
                <h4>🐍 Python Version</h4>
                <div className="info-value">{systemInfo.python_version}</div>
              </div>

              <div className="info-card">
                <h4>💻 Platform</h4>
                <div className="info-value">{systemInfo.platform}</div>
              </div>

              <div className="info-card">
                <h4>📁 Project Root</h4>
                <div className="info-value mono">{systemInfo.project_root}</div>
              </div>

              <div className="info-card">
                <h4>💾 Input Directory Size</h4>
                <div className="info-value">
                  {(systemInfo.disk_usage.input / 1024 / 1024).toFixed(2)} MB
                </div>
              </div>

              <div className="info-card">
                <h4>📊 Output Directory Size</h4>
                <div className="info-value">
                  {(systemInfo.disk_usage.output / 1024 / 1024).toFixed(2)} MB
                </div>
              </div>
            </div>

            <div className="system-commands">
              <h4>System Commands</h4>
              <div className="command-buttons">
                <button className="cmd-btn" title="Refresh system data" onClick={fetchSystemInfo}>
                  🔄 Refresh
                </button>
                <button className="cmd-btn" title="Export configuration" onClick={() => alert('Export feature coming soon')}>
                  📥 Export Config
                </button>
                <button className="cmd-btn" title="Import configuration" onClick={() => alert('Import feature coming soon')}>
                  📤 Import Config
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AdvancedSettings;
