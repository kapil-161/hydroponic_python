import React, { useEffect, useState } from 'react';
import axios from 'axios';
import './ParameterEditor.css';

const ParameterEditor = () => {
  const [parameters, setParameters] = useState({});
  const [selectedFile, setSelectedFile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [editedValues, setEditedValues] = useState({});
  const [searchQuery, setSearchQuery] = useState('');
  const [saveStatus, setSaveStatus] = useState(null);
  const [viewMode, setViewMode] = useState('grid'); // 'grid' or 'table'

  useEffect(() => {
    fetchParameters();
  }, []);

  const fetchParameters = async () => {
    try {
      setLoading(true);
      const response = await axios.get('http://localhost:5001/api/parameters');
      setParameters(response.data);
      const firstFile = Object.keys(response.data)[0];
      setSelectedFile(firstFile);
      setError(null);
    } catch (err) {
      setError('Failed to load parameters: ' + err.message);
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleValueChange = (paramName, newValue) => {
    setEditedValues((prev) => ({
      ...prev,
      [paramName]: newValue,
    }));
  };

  const handleSaveParameter = async (paramName) => {
    try {
      const newValue = editedValues[paramName];
      if (newValue === undefined) return;

      await axios.put(
        `http://localhost:5001/api/parameters/${selectedFile}/${paramName}`,
        { value: newValue }
      );

      // Update the parameters state
      setParameters((prev) => ({
        ...prev,
        [selectedFile]: {
          ...prev[selectedFile],
          [paramName]: {
            ...prev[selectedFile][paramName],
            value: newValue,
          },
        },
      }));

      // Clear edited value
      setEditedValues((prev) => {
        const newEdited = { ...prev };
        delete newEdited[paramName];
        return newEdited;
      });

      setSaveStatus({ type: 'success', message: `${paramName} saved!` });
      setTimeout(() => setSaveStatus(null), 3000);
    } catch (err) {
      setSaveStatus({ type: 'error', message: 'Failed to save: ' + err.message });
      console.error(err);
    }
  };

  const handleSaveAll = async () => {
    try {
      const updates = Object.entries(editedValues);
      let successCount = 0;

      for (const [paramName, value] of updates) {
        try {
          await axios.put(
            `http://localhost:5001/api/parameters/${selectedFile}/${paramName}`,
            { value }
          );
          successCount++;
        } catch (err) {
          console.error(`Failed to save ${paramName}:`, err);
        }
      }

      setSaveStatus({
        type: 'success',
        message: `Saved ${successCount} of ${updates.length} parameters!`,
      });
      setEditedValues({});
      setTimeout(() => setSaveStatus(null), 3000);
    } catch (err) {
      setSaveStatus({ type: 'error', message: 'Failed to save all: ' + err.message });
    }
  };

  if (loading) {
    return <div className="loading">Loading parameters...</div>;
  }

  if (error) {
    return <div className="error">{error}</div>;
  }

  const currentParams = selectedFile ? parameters[selectedFile] : {};
  const filteredParams = Object.entries(currentParams).filter(([name, param]) => {
    const searchLower = searchQuery.toLowerCase();
    return (
      name.toLowerCase().includes(searchLower) ||
      param.description?.toLowerCase().includes(searchLower)
    );
  });

  const hasEdits = Object.keys(editedValues).length > 0;

  return (
    <div className="parameter-editor">
      <div className="editor-sidebar">
        <h3>Parameter Files</h3>
        <div className="file-list">
          {Object.keys(parameters).map((file) => (
            <button
              key={file}
              className={`file-btn ${selectedFile === file ? 'active' : ''}`}
              onClick={() => {
                setSelectedFile(file);
                setEditedValues({});
              }}
            >
              <span className="file-icon">📄</span>
              <span className="file-name">{file}</span>
              <span className="param-count">
                {Object.keys(parameters[file]).length}
              </span>
            </button>
          ))}
        </div>
      </div>

      <div className="editor-main">
        {selectedFile && (
          <>
            <div className="editor-header">
              <div>
                <h2>{selectedFile}</h2>
                <p>{filteredParams.length} parameters shown</p>
              </div>
              <div style={{display: 'flex', gap: '10px', alignItems: 'center'}}>
                <button
                  className={`view-mode-btn ${viewMode === 'grid' ? 'active' : ''}`}
                  onClick={() => setViewMode('grid')}
                  title="Grid view"
                >
                  ⊞ Grid
                </button>
                <button
                  className={`view-mode-btn ${viewMode === 'table' ? 'active' : ''}`}
                  onClick={() => setViewMode('table')}
                  title="Table view"
                >
                  ≡ Table
                </button>
                {hasEdits && (
                  <button className="btn-save-all" onClick={handleSaveAll}>
                    💾 Save All ({Object.keys(editedValues).length})
                  </button>
                )}
              </div>
            </div>

            <div className="editor-search">
              <input
                type="text"
                placeholder="Search parameters by name or description..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="search-input"
              />
            </div>

            {saveStatus && (
              <div className={`save-status ${saveStatus.type}`}>
                {saveStatus.message}
              </div>
            )}

            {viewMode === 'grid' ? (
              <div className="parameters-grid">
                {filteredParams.map(([name, param]) => {
                  const isEdited = editedValues[name] !== undefined;
                  const displayValue = isEdited ? editedValues[name] : param.value;

                  return (
                    <div
                      key={name}
                      className={`param-card ${isEdited ? 'edited' : ''}`}
                    >
                      <div className="param-name">{name}</div>

                      {param.description && (
                        <div className="param-description">{param.description}</div>
                      )}

                      <div className="param-meta">
                        {param.unit && <span className="unit">{param.unit}</span>}
                        {param.min && param.max && (
                          <span className="range">
                            {param.min} - {param.max}
                          </span>
                        )}
                      </div>

                      <div className="param-input-group">
                        <input
                          type="text"
                          value={displayValue}
                          onChange={(e) => handleValueChange(name, e.target.value)}
                          className={`param-input ${isEdited ? 'changed' : ''}`}
                          placeholder="Enter value"
                        />

                        {isEdited && (
                          <button
                            className="btn-save"
                            onClick={() => handleSaveParameter(name)}
                            title="Save this parameter"
                          >
                            ✓
                          </button>
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

                {filteredParams.length === 0 && (
                  <div className="no-results">
                    No parameters match your search
                  </div>
                )}
              </div>
            ) : (
              <table className="parameters-table">
                <thead>
                  <tr>
                    <th>Parameter Name</th>
                    <th>Value</th>
                    <th>Unit</th>
                    <th>Description</th>
                    <th>Min</th>
                    <th>Max</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredParams.map(([name, param]) => {
                    const isEdited = editedValues[name] !== undefined;
                    const displayValue = isEdited ? editedValues[name] : param.value;
                    return (
                      <tr key={name} className={isEdited ? 'edited-row' : ''}>
                        <td className="param-name-col">{name}</td>
                        <td>
                          <input
                            type="text"
                            value={displayValue}
                            onChange={(e) => handleValueChange(name, e.target.value)}
                            className="param-input-table"
                          />
                        </td>
                        <td>{param.unit || '-'}</td>
                        <td className="desc-col">{param.description || '-'}</td>
                        <td>{param.min || '-'}</td>
                        <td>{param.max || '-'}</td>
                        <td>
                          {isEdited ? (
                            <button
                              className="btn-save-table"
                              onClick={() => handleSaveParameter(name)}
                            >
                              Save
                            </button>
                          ) : (
                            <span>-</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default ParameterEditor;
