import React, { useState, useEffect } from 'react';
import './ResultsViewer.css';

const ResultsViewer = ({ results }) => {
  const [activeFile, setActiveFile] = useState(null);
  const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' });

  useEffect(() => {
    if (results && Object.keys(results).length > 0) {
      setActiveFile(Object.keys(results)[0]);
    }
  }, [results]);

  const handleSort = (key) => {
    let direction = 'asc';
    if (sortConfig.key === key && sortConfig.direction === 'asc') {
      direction = 'desc';
    }
    setSortConfig({ key, direction });
  };

  const getSortedData = () => {
    if (!activeFile || !results[activeFile]) return [];

    const data = [...results[activeFile]];

    if (sortConfig.key) {
      data.sort((a, b) => {
        const aValue = a[sortConfig.key];
        const bValue = b[sortConfig.key];

        if (aValue === null) return 1;
        if (bValue === null) return -1;
        if (aValue === null && bValue === null) return 0;

        if (typeof aValue === 'number' && typeof bValue === 'number') {
          return sortConfig.direction === 'asc' ? aValue - bValue : bValue - aValue;
        }

        const aStr = String(aValue).toLowerCase();
        const bStr = String(bValue).toLowerCase();

        return sortConfig.direction === 'asc'
          ? aStr.localeCompare(bStr)
          : bStr.localeCompare(aStr);
      });
    }

    return data;
  };

  const formatValue = (value) => {
    if (typeof value === 'number') {
      return value.toFixed(4);
    }
    return String(value);
  };

  const getColumns = () => {
    if (!activeFile || !results[activeFile] || results[activeFile].length === 0) {
      return [];
    }
    return Object.keys(results[activeFile][0]);
  };

  const columns = getColumns();
  const sortedData = getSortedData();

  return (
    <div className="results-viewer">
      <div className="results-header">
        <h2>Simulation Results</h2>
        <p>View and analyze simulation output data</p>
      </div>

      <div className="results-container">
        <div className="results-sidebar">
          <h3>Output Files</h3>
          <div className="file-list">
            {results &&
              Object.keys(results).map((file) => (
                <button
                  key={file}
                  className={`file-btn ${activeFile === file ? 'active' : ''}`}
                  onClick={() => setActiveFile(file)}
                >
                  <span className="file-icon">📊</span>
                  <span className="file-name">{file}</span>
                  <span className="row-count">
                    {results[file]?.length || 0} rows
                  </span>
                </button>
              ))}
          </div>
        </div>

        <div className="results-main">
          {activeFile && results[activeFile] && (
            <>
              <div className="results-header-info">
                <h3>{activeFile}</h3>
                <p>{sortedData.length} rows × {columns.length} columns</p>
              </div>

              {sortedData.length > 0 ? (
                <div className="table-container">
                  <table className="results-table">
                    <thead>
                      <tr>
                        {columns.map((col) => (
                          <th
                            key={col}
                            onClick={() => handleSort(col)}
                            className={`sortable ${
                              sortConfig.key === col ? 'active' : ''
                            }`}
                          >
                            <div className="header-content">
                              {col}
                              {sortConfig.key === col && (
                                <span className="sort-icon">
                                  {sortConfig.direction === 'asc' ? '▲' : '▼'}
                                </span>
                              )}
                            </div>
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {sortedData.map((row, idx) => (
                        <tr key={idx} className={idx % 2 === 0 ? 'even' : 'odd'}>
                          {columns.map((col) => (
                            <td key={`${idx}-${col}`}>
                              {formatValue(row[col])}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="no-data">No data available in this file</div>
              )}
            </>
          )}
        </div>
      </div>

      <div className="results-info">
        <h3>About Results Files</h3>

        <div className="info-grid">
          <div className="info-card">
            <h4>📊 simulation_results.csv</h4>
            <p>Overall simulation metrics including plant growth, resource usage, and stress indicators.</p>
          </div>

          <div className="info-card">
            <h4>🌿 biomass_allocation.csv</h4>
            <p>Partitioning of biomass across shoots, roots, leaves, and fruits. Tracks organ development.</p>
          </div>

          <div className="info-card">
            <h4>☀️ photosynthesis.csv</h4>
            <p>CO2 assimilation rates, light response curves, and photosynthetic efficiency.</p>
          </div>

          <div className="info-card">
            <h4>💧 water_uptake.csv</h4>
            <p>Water extraction from soil, transpiration rates, and water stress indicators.</p>
          </div>

          <div className="info-card">
            <h4>🧬 nitrogen_balance.csv</h4>
            <p>Nitrogen uptake, remobilization, and concentration in plant tissues.</p>
          </div>

          <div className="info-card">
            <h4>📈 Additional Outputs</h4>
            <p>Includes canopy structure, leaf development, root distribution, and stress dynamics.</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ResultsViewer;
