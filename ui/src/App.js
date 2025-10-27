import React, { useState } from 'react';
import './App.css';
import ModelGraph from './components/ModelGraph';
import ParameterEditor from './components/ParameterEditor';
import ParameterTracker from './components/ParameterTracker';
import AdvancedSettings from './components/AdvancedSettings';
import SimulationControl from './components/SimulationControl';
import ResultsViewer from './components/ResultsViewer';

function App() {
  const [activeTab, setActiveTab] = useState('graph');
  const [simulationRunning, setSimulationRunning] = useState(false);
  const [simulationResults, setSimulationResults] = useState(null);

  const handleRunSimulation = (results) => {
    setSimulationResults(results);
    setActiveTab('results');
  };

  return (
    <div className="App">
      <header className="app-header">
        <h1>🌱 Hydroponic System Simulator</h1>
        <p>Interactive visualization and parameter control</p>
      </header>

      <nav className="app-nav">
        <button
          className={`nav-btn ${activeTab === 'graph' ? 'active' : ''}`}
          onClick={() => setActiveTab('graph')}
        >
          System Graph
        </button>
        <button
          className={`nav-btn ${activeTab === 'params' ? 'active' : ''}`}
          onClick={() => setActiveTab('params')}
        >
          Parameters
        </button>
        <button
          className={`nav-btn ${activeTab === 'tracker' ? 'active' : ''}`}
          onClick={() => setActiveTab('tracker')}
        >
          Parameter Tracker
        </button>
        <button
          className={`nav-btn ${activeTab === 'advanced' ? 'active' : ''}`}
          onClick={() => setActiveTab('advanced')}
        >
          Advanced Settings
        </button>
        <button
          className={`nav-btn ${activeTab === 'simulate' ? 'active' : ''}`}
          onClick={() => setActiveTab('simulate')}
        >
          Run Simulation
        </button>
        {simulationResults && (
          <button
            className={`nav-btn ${activeTab === 'results' ? 'active' : ''}`}
            onClick={() => setActiveTab('results')}
          >
            Results
          </button>
        )}
      </nav>

      <main className="app-content">
        {activeTab === 'graph' && <ModelGraph />}
        {activeTab === 'params' && <ParameterEditor />}
        {activeTab === 'tracker' && <ParameterTracker />}
        {activeTab === 'advanced' && <AdvancedSettings />}
        {activeTab === 'simulate' && (
          <SimulationControl
            onSimulationComplete={handleRunSimulation}
            isRunning={simulationRunning}
          />
        )}
        {activeTab === 'results' && simulationResults && (
          <ResultsViewer results={simulationResults} />
        )}
      </main>
    </div>
  );
}

export default App;
