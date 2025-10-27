import React, { useState } from 'react';
import axios from 'axios';
import './SimulationControl.css';

const SimulationControl = ({ onSimulationComplete, isRunning }) => {
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);
  const [output, setOutput] = useState('');

  const handleRunSimulation = async () => {
    try {
      setRunning(true);
      setError(null);
      setOutput('');
      setProgress(10);
      setStatus('Starting simulation...');

      const response = await axios.post('http://localhost:5001/api/simulation/run');

      if (response.data.success) {
        setProgress(50);
        setStatus('Simulation completed! Fetching results...');

        // Fetch results
        const resultsResponse = await axios.get('http://localhost:5001/api/simulation/results');
        setProgress(100);
        setStatus('Results loaded!');
        setOutput(response.data.output);

        setTimeout(() => {
          onSimulationComplete(resultsResponse.data);
        }, 500);
      } else {
        setError('Simulation failed: ' + response.data.error);
      }
    } catch (err) {
      setError('Error running simulation: ' + err.message);
      console.error(err);
    } finally {
      setRunning(false);
      setTimeout(() => setStatus(null), 3000);
    }
  };

  return (
    <div className="simulation-control">
      <div className="control-header">
        <h2>Run Simulation</h2>
        <p>Execute the hydroponic system simulation with current parameters</p>
      </div>

      <div className="control-panel">
        <div className="control-info">
          <div className="info-item">
            <span className="info-label">Status:</span>
            <span className="info-value">{running ? '⏳ Running...' : '✓ Ready'}</span>
          </div>
          <div className="info-item">
            <span className="info-label">Progress:</span>
            <span className="info-value">{progress}%</span>
          </div>
        </div>

        <button
          className={`btn-run ${running ? 'disabled' : ''}`}
          onClick={handleRunSimulation}
          disabled={running}
        >
          {running ? '⏳ Running Simulation...' : '▶ Run Simulation'}
        </button>
      </div>

      {progress > 0 && (
        <div className="progress-container">
          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{ width: `${progress}%` }}
            ></div>
          </div>
          <p className="progress-text">{progress}%</p>
        </div>
      )}

      {status && (
        <div className="status-message">
          {status}
        </div>
      )}

      {error && (
        <div className="error-message">
          <strong>Error:</strong> {error}
        </div>
      )}

      {output && (
        <div className="output-container">
          <h3>Simulation Output</h3>
          <pre className="output-text">{output}</pre>
        </div>
      )}

      <div className="simulation-info">
        <h3>Before Running</h3>
        <ul>
          <li>✓ Verify all parameters in the Parameters tab</li>
          <li>✓ Check weather data is available</li>
          <li>✓ Ensure CSV files are properly formatted</li>
          <li>✓ Review model graph for data flow</li>
        </ul>

        <h3>What Happens During Simulation</h3>
        <ol>
          <li><strong>Phenology</strong> - Calculates plant development stages</li>
          <li><strong>Root System</strong> - Determines root growth and distribution</li>
          <li><strong>Water Uptake</strong> - Calculates water extraction and transpiration</li>
          <li><strong>Nutrient Models</strong> - Computes nutrient availability and uptake</li>
          <li><strong>Leaf Development</strong> - Tracks leaf morphology and expansion</li>
          <li><strong>Stress Models</strong> - Evaluates 7 types of stress factors</li>
          <li><strong>Canopy</strong> - Determines leaf area index and light interception</li>
          <li><strong>Photosynthesis</strong> - Calculates CO2 assimilation</li>
          <li><strong>Respiration</strong> - Computes respiration costs</li>
          <li><strong>Biomass Allocation</strong> - Partitions assimilates to organs</li>
          <li><strong>Nitrogen Balance</strong> - Tracks nitrogen pools and remobilization</li>
        </ol>

        <h3>Output Files</h3>
        <ul>
          <li>📊 simulation_results.csv - Overall simulation results</li>
          <li>📊 biomass_allocation.csv - Organ-specific biomass</li>
          <li>📊 photosynthesis.csv - Assimilation rates</li>
          <li>📊 water_uptake.csv - Water and transpiration</li>
          <li>📊 nitrogen_balance.csv - Nitrogen dynamics</li>
        </ul>
      </div>
    </div>
  );
};

export default SimulationControl;
