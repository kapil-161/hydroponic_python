// CROPGRO Hydroponic Simulator - JavaScript Application Logic

// Global variables
let currentResults = null;
let currentCharts = {};

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    console.log('🌱 CROPGRO Hydroponic Simulator - Web UI Loading...');
    
    // Initialize default values
    loadDefaults();
    
    // Initialize nutrient inputs
    initializeNutrientInputs();
    
    // Set default weather date
    document.getElementById('weather_start_date').value = new Date().toISOString().split('T')[0];
    
    console.log('✅ Application initialized successfully');
});

// Load default configuration values
async function loadDefaults() {
    try {
        const response = await fetch('/api/defaults');
        if (response.ok) {
            const defaults = await response.json();
            
            // Populate form fields with defaults
            populateSystemDefaults(defaults.system);
            populateCropDefaults(defaults.crop);
            populateNutrientDefaults(defaults.nutrients);
            
            console.log('✅ Default values loaded');
        } else {
            console.error('❌ Failed to load defaults');
            showAlert('Failed to load default values', 'warning');
            // Use fallback defaults
            initializeNutrientInputs();
        }
    } catch (error) {
        console.error('❌ Error loading defaults:', error);
        showAlert('Error loading default values', 'danger');
        // Use fallback defaults
        initializeNutrientInputs();
    }
}

// Populate system configuration defaults
function populateSystemDefaults(systemDefaults) {
    document.getElementById('system_id').value = systemDefaults.system_id || 'CROPGRO_001';
    document.getElementById('system_type').value = systemDefaults.system_type || 'NFT';
    document.getElementById('tank_volume').value = systemDefaults.tank_volume || 1500;
    document.getElementById('flow_rate').value = systemDefaults.flow_rate || 50;
    document.getElementById('system_area').value = systemDefaults.system_area || 10;
    document.getElementById('n_plants').value = systemDefaults.n_plants || 48;
}

// Populate crop parameter defaults
function populateCropDefaults(cropDefaults) {
    document.getElementById('kcb').value = cropDefaults.kcb || 1.05;
    document.getElementById('phi').value = cropDefaults.phi || 0.8;
    document.getElementById('crop_height').value = cropDefaults.crop_height || 0.2;
    document.getElementById('laid').value = cropDefaults.laid || 3.0;
}

// Populate nutrient defaults
function populateNutrientDefaults(nutrientDefaults) {
    window.defaultNutrients = nutrientDefaults;
    initializeNutrientInputs();
}

// Initialize nutrient input fields
function initializeNutrientInputs() {
    const nutrientContainer = document.getElementById('nutrient_inputs');
    
    // Define nutrient list (if defaults not loaded yet)
    const nutrients = window.defaultNutrients || {
        'N-NO3': { initial_conc: 200.0, molar_mass: 62.0, charge: -1 },
        'P': { initial_conc: 50.0, molar_mass: 31.0, charge: 3 },
        'K': { initial_conc: 200.0, molar_mass: 39.1, charge: 1 },
        'Ca': { initial_conc: 150.0, molar_mass: 40.1, charge: 2 },
        'Mg': { initial_conc: 50.0, molar_mass: 24.3, charge: 2 },
        'S': { initial_conc: 60.0, molar_mass: 32.1, charge: 2 },
        'Fe': { initial_conc: 3.0, molar_mass: 55.8, charge: 2 },
        'Mn': { initial_conc: 1.0, molar_mass: 54.9, charge: 2 },
        'Zn': { initial_conc: 0.3, molar_mass: 65.4, charge: 2 },
        'Cu': { initial_conc: 0.1, molar_mass: 63.5, charge: 2 },
        'B': { initial_conc: 0.5, molar_mass: 10.8, charge: 3 },
        'Mo': { initial_conc: 0.05, molar_mass: 95.9, charge: 4 }
    };
    
    nutrientContainer.innerHTML = '';
    
    const nutrientGrid = document.createElement('div');
    nutrientGrid.className = 'nutrient-grid';
    
    Object.keys(nutrients).forEach(nutrientId => {
        const nutrient = nutrients[nutrientId];
        
        const nutrientItem = document.createElement('div');
        nutrientItem.className = 'nutrient-item';
        
        nutrientItem.innerHTML = `
            <label class="nutrient-label">${nutrientId}</label>
            <div class="input-group input-group-sm">
                <input type="number" 
                       id="nutrient_${nutrientId.replace('-', '_')}" 
                       class="form-control" 
                       value="${nutrient.initial_conc}" 
                       step="0.1" 
                       min="0">
                <span class="input-group-text">mg/L</span>
            </div>
            <small class="text-muted">MW: ${nutrient.molar_mass} g/mol</small>
        `;
        
        nutrientGrid.appendChild(nutrientItem);
    });
    
    nutrientContainer.appendChild(nutrientGrid);
}

// Toggle simulation mode options
function toggleSimulationMode() {
    const simulationMode = document.getElementById('simulation_mode').value;
    const maturityOptions = document.getElementById('maturity_options');
    const fixedDaysOptions = document.getElementById('fixed_days_options');
    
    if (simulationMode === 'maturity') {
        maturityOptions.style.display = 'block';
        fixedDaysOptions.style.display = 'none';
    } else {
        maturityOptions.style.display = 'none';
        fixedDaysOptions.style.display = 'block';
    }
}

// Toggle genetic parameter overrides
function toggleGeneticOverrides() {
    const enableOverride = document.getElementById('enable_genetic_override').checked;
    const overridesDiv = document.getElementById('genetic_overrides');
    
    if (enableOverride) {
        overridesDiv.style.display = 'block';
    } else {
        overridesDiv.style.display = 'none';
    }
}

// Add event listener for genetic override checkbox
document.addEventListener('DOMContentLoaded', function() {
    const geneticCheckbox = document.getElementById('enable_genetic_override');
    if (geneticCheckbox) {
        geneticCheckbox.addEventListener('change', toggleGeneticOverrides);
    }
});

// Toggle weather input methods
function toggleWeatherInputs() {
    const weatherType = document.getElementById('weather_type').value;
    const generateDiv = document.getElementById('weather_generate');
    const customDiv = document.getElementById('weather_custom');
    
    if (weatherType === 'generate') {
        generateDiv.style.display = 'block';
        customDiv.style.display = 'none';
        customDiv.classList.remove('show');
    } else {
        generateDiv.style.display = 'none';
        customDiv.style.display = 'block';
        customDiv.classList.add('show');
        
        // Add initial weather day if none exist
        if (document.querySelectorAll('.weather-day-row').length === 0) {
            addWeatherDay();
        }
    }
}

// Add custom weather day input
function addWeatherDay() {
    const container = document.getElementById('custom_weather_days');
    const dayCount = container.children.length + 1;
    const today = new Date();
    today.setDate(today.getDate() + dayCount - 1);
    
    const weatherDay = document.createElement('div');
    weatherDay.className = 'weather-day-row fade-in';
    
    weatherDay.innerHTML = `
        <div class="d-flex justify-content-between align-items-center mb-2">
            <h6 class="mb-0">Day ${dayCount}</h6>
            <button type="button" class="btn btn-sm btn-outline-danger" onclick="removeWeatherDay(this)">
                <i class="fas fa-trash"></i>
            </button>
        </div>
        <div class="row">
            <div class="col-4">
                <label class="form-label">Date</label>
                <input type="date" class="form-control weather-date" value="${today.toISOString().split('T')[0]}">
            </div>
            <div class="col-4">
                <label class="form-label">Avg Temp (°C)</label>
                <input type="number" class="form-control weather-temp-avg" value="22" step="0.1">
            </div>
            <div class="col-4">
                <label class="form-label">Min Temp (°C)</label>
                <input type="number" class="form-control weather-temp-min" value="18" step="0.1">
            </div>
        </div>
        <div class="row mt-2">
            <div class="col-4">
                <label class="form-label">Max Temp (°C)</label>
                <input type="number" class="form-control weather-temp-max" value="26" step="0.1">
            </div>
            <div class="col-4">
                <label class="form-label">Solar Rad (MJ/m²)</label>
                <input type="number" class="form-control weather-solar" value="18" step="0.1">
            </div>
            <div class="col-4">
                <label class="form-label">Humidity (%)</label>
                <input type="number" class="form-control weather-humidity" value="70" step="1" min="0" max="100">
            </div>
        </div>
        <div class="row mt-2">
            <div class="col-6">
                <label class="form-label">Wind Speed (m/s)</label>
                <input type="number" class="form-control weather-wind" value="2.0" step="0.1" min="0">
            </div>
            <div class="col-6">
                <label class="form-label">Rainfall (mm)</label>
                <input type="number" class="form-control weather-rainfall" value="0" step="0.1" min="0">
            </div>
        </div>
    `;
    
    container.appendChild(weatherDay);
}

// Remove weather day input
function removeWeatherDay(button) {
    const weatherRow = button.closest('.weather-day-row');
    weatherRow.remove();
    
    // Renumber remaining days
    const weatherDays = document.querySelectorAll('.weather-day-row');
    weatherDays.forEach((day, index) => {
        day.querySelector('h6').textContent = `Day ${index + 1}`;
    });
}

// Collect form data for simulation
function collectFormData() {
    const simulationMode = document.getElementById('simulation_mode').value;
    
    const formData = {
        simulation: {
            cultivar_id: document.getElementById('cultivar_id').value,
            simulation_mode: simulationMode,
            ...(simulationMode === 'maturity' ? {
                target_maturity: document.getElementById('target_maturity').value,
                max_days: parseInt(document.getElementById('max_days').value)
            } : {
                simulation_days: parseInt(document.getElementById('simulation_days').value)
            })
        },
        system: {
            system_id: document.getElementById('system_id').value,
            crop_id: 'LETTUCE_001',
            location_id: 'GREENHOUSE_001',
            tank_volume: parseFloat(document.getElementById('tank_volume').value),
            flow_rate: parseFloat(document.getElementById('flow_rate').value),
            system_type: document.getElementById('system_type').value,
            system_area: parseFloat(document.getElementById('system_area').value),
            n_plants: parseInt(document.getElementById('n_plants').value),
            description: 'Web UI Generated System'
        },
        crop: {
            crop_id: 'LETTUCE_001',
            crop_name: 'Hydroponic Lettuce',
            kcb: parseFloat(document.getElementById('kcb').value),
            phi: parseFloat(document.getElementById('phi').value),
            crop_height: parseFloat(document.getElementById('crop_height').value),
            root_zone_depth: 0.15,
            laid: parseFloat(document.getElementById('laid').value)
        },
        weather: collectWeatherData(),
        nutrients: collectNutrientData(),
        environmental_control: collectEnvironmentalData(),
        genetic_overrides: collectGeneticOverrides(),
        growth_parameters: collectGrowthParameters(),
        initial_state: collectInitialState()
    };
    
    return formData;
}

// Collect weather data based on selected type
function collectWeatherData() {
    const weatherType = document.getElementById('weather_type').value;
    
    if (weatherType === 'generate') {
        return {
            type: 'generate',
            start_date: document.getElementById('weather_start_date').value,
            base_temp: parseFloat(document.getElementById('base_temp').value)
        };
    } else {
        // Collect custom weather data
        const weatherDays = [];
        const dayRows = document.querySelectorAll('.weather-day-row');
        
        dayRows.forEach(row => {
            const dayData = {
                date: row.querySelector('.weather-date').value,
                temp_avg: parseFloat(row.querySelector('.weather-temp-avg').value),
                temp_min: parseFloat(row.querySelector('.weather-temp-min').value),
                temp_max: parseFloat(row.querySelector('.weather-temp-max').value),
                solar_radiation: parseFloat(row.querySelector('.weather-solar').value),
                rel_humidity: parseFloat(row.querySelector('.weather-humidity').value),
                wind_speed: parseFloat(row.querySelector('.weather-wind').value),
                rainfall: parseFloat(row.querySelector('.weather-rainfall').value)
            };
            weatherDays.push(dayData);
        });
        
        return {
            type: 'custom',
            daily_data: weatherDays
        };
    }
}

// Collect nutrient data
function collectNutrientData() {
    const nutrients = {};
    const nutrientInputs = document.querySelectorAll('[id^="nutrient_"]');
    
    const nutrientMap = {
        'N_NO3': 'N-NO3',
        'P': 'P',
        'K': 'K',
        'Ca': 'Ca',
        'Mg': 'Mg',
        'S': 'S',
        'Fe': 'Fe',
        'Mn': 'Mn',
        'Zn': 'Zn',
        'Cu': 'Cu',
        'B': 'B',
        'Mo': 'Mo'
    };
    
    // Default nutrient properties for fallback
    const defaultNutrientProps = {
        'N-NO3': { molar_mass: 62.0, charge: -1 },
        'P': { molar_mass: 31.0, charge: 3 },
        'K': { molar_mass: 39.1, charge: 1 },
        'Ca': { molar_mass: 40.1, charge: 2 },
        'Mg': { molar_mass: 24.3, charge: 2 },
        'S': { molar_mass: 32.1, charge: 2 },
        'Fe': { molar_mass: 55.8, charge: 2 },
        'Mn': { molar_mass: 54.9, charge: 2 },
        'Zn': { molar_mass: 65.4, charge: 2 },
        'Cu': { molar_mass: 63.5, charge: 2 },
        'B': { molar_mass: 10.8, charge: 3 },
        'Mo': { molar_mass: 95.9, charge: 4 }
    };
    
    nutrientInputs.forEach(input => {
        const inputId = input.id.replace('nutrient_', '');
        const nutrientId = nutrientMap[inputId] || inputId;
        
        // Get default properties for this nutrient
        const defaultNutrient = window.defaultNutrients?.[nutrientId] || 
                               defaultNutrientProps[nutrientId] || 
                               { molar_mass: 50.0, charge: 1 };
        
        const concentration = parseFloat(input.value) || 0.0;
        
        nutrients[nutrientId] = {
            initial_conc: concentration,
            molar_mass: defaultNutrient.molar_mass || 50.0,
            charge: defaultNutrient.charge || 1
        };
    });
    
    return nutrients;
}

// Collect environmental control data
function collectEnvironmentalData() {
    return {
        control_strategy: document.getElementById('control_strategy').value,
        target_vpd: parseFloat(document.getElementById('target_vpd').value) || 0.8,
        day_temp: parseFloat(document.getElementById('day_temp').value) || 22.0,
        night_temp: parseFloat(document.getElementById('night_temp').value) || 18.0,
        target_co2: parseFloat(document.getElementById('target_co2').value) || 1200.0,
        light_hours: parseFloat(document.getElementById('light_hours').value) || 16.0,
        light_intensity: parseFloat(document.getElementById('light_intensity').value) || 200.0
    };
}

// Collect genetic override data
function collectGeneticOverrides() {
    const enableOverride = document.getElementById('enable_genetic_override').checked;
    
    if (!enableOverride) {
        return { enabled: false };
    }
    
    return {
        enabled: true,
        lfmax: parseFloat(document.getElementById('lfmax').value) || 1.2,
        slavr: parseFloat(document.getElementById('slavr').value) || 180.0,
        ec_tolerance: parseFloat(document.getElementById('ec_tolerance').value) || 1.3,
        nitrate_efficiency: parseFloat(document.getElementById('nitrate_efficiency').value) || 0.85,
        root_activity: parseFloat(document.getElementById('root_activity').value) || 1.0
    };
}

// Collect growth parameters
function collectGrowthParameters() {
    return {
        base_temperature: parseFloat(document.getElementById('base_temperature').value) || 4.0,
        max_temperature: parseFloat(document.getElementById('max_temperature').value) || 35.0,
        water_stress: parseFloat(document.getElementById('water_stress').value) || 0.9,
        stress_acceleration: parseFloat(document.getElementById('stress_acceleration').value) || 1.5,
        photoperiod_sensitive: document.getElementById('photoperiod_sensitive').value === 'true'
    };
}

// Collect initial state data
function collectInitialState() {
    return {
        initial_lai: parseFloat(document.getElementById('initial_lai').value) || 0.8,
        initial_height: parseFloat(document.getElementById('initial_height').value) || 8.0,
        plant_density: parseFloat(document.getElementById('plant_density').value) || 25.0
    };
}

// Run the simulation
async function runSimulation() {
    try {
        console.log('🚀 Starting CROPGRO simulation...');
        
        // Update status
        updateSimulationStatus('Running', 'running');
        
        // Show loading modal
        const loadingModal = new bootstrap.Modal(document.getElementById('loadingModal'));
        loadingModal.show();
        
        // Animate progress bar
        animateProgressBar();
        
        // Collect form data
        const formData = collectFormData();
        console.log('📋 Form data collected:', formData);
        
        // Validate data
        if (!validateFormData(formData)) {
            throw new Error('Invalid form data - please check your inputs');
        }
        
        // Send request to backend with timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 120000); // 2 minute timeout
        
        const response = await fetch('/api/simulate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData),
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        const result = await response.json();
        
        if (!response.ok || !result.success) {
            throw new Error(result.error || 'Simulation failed');
        }
        
        console.log('✅ Simulation completed successfully');
        
        // Clear progress interval and complete progress bar
        if (window.progressInterval) {
            clearInterval(window.progressInterval);
        }
        const progressBar = document.getElementById('progress_bar');
        progressBar.style.width = '100%';
        
        // Store results
        currentResults = result;
        
        // Small delay to show 100% completion
        setTimeout(() => {
            // Hide loading modal
            loadingModal.hide();
            
            // Update status
            updateSimulationStatus('Complete', 'complete');
            
            // Display results
            displayResults(result);
            
            // Show success message
            showAlert('Simulation completed successfully!', 'success');
        }, 500);
        
    } catch (error) {
        console.error('❌ Simulation error:', error);
        
        // Clear progress interval
        if (window.progressInterval) {
            clearInterval(window.progressInterval);
        }
        
        // Hide loading modal
        const loadingModal = bootstrap.Modal.getInstance(document.getElementById('loadingModal'));
        if (loadingModal) {
            loadingModal.hide();
        }
        
        // Update status
        updateSimulationStatus('Error', 'error');
        
        // Handle different error types
        let errorMessage = 'Simulation failed';
        if (error.name === 'AbortError') {
            errorMessage = 'Simulation timed out (exceeded 2 minutes)';
        } else if (error.message) {
            errorMessage = `Simulation failed: ${error.message}`;
        }
        
        // Show error message
        showAlert(errorMessage, 'danger');
    }
}

// Validate form data
function validateFormData(formData) {
    try {
        // Check required fields
        if (!formData.simulation.cultivar_id || formData.simulation.simulation_days < 1) {
            return false;
        }
        
        if (!formData.system.system_id || formData.system.tank_volume <= 0) {
            return false;
        }
        
        if (formData.weather.type === 'custom' && formData.weather.daily_data.length === 0) {
            return false;
        }
        
        return true;
    } catch (error) {
        return false;
    }
}

// Update simulation status
function updateSimulationStatus(status, type) {
    const statusElement = document.getElementById('simulation_status');
    statusElement.textContent = status;
    statusElement.className = `badge status-${type}`;
}

// Animate progress bar during simulation
function animateProgressBar() {
    const progressBar = document.getElementById('progress_bar');
    let progress = 0;
    
    const interval = setInterval(() => {
        progress += Math.random() * 10 + 5; // 5-15% increments
        if (progress >= 95) {
            progress = 95; // Stop at 95% until completion
            clearInterval(interval);
        }
        progressBar.style.width = progress + '%';
    }, 800);
    
    // Store interval ID to clear it later
    window.progressInterval = interval;
}

// Display simulation results
function displayResults(results) {
    // Hide initial message
    document.getElementById('initial_message').style.display = 'none';
    
    // Show results container
    document.getElementById('results_container').classList.remove('d-none');
    
    // Display summary statistics
    displaySummaryStats(results.summary);
    
    // Display charts
    displayCharts(results);
    
    // Display detailed data
    displayDetailedData(results.daily_results);
    
    // Display genetics information
    displayGeneticsInfo(results);
}

// Display summary statistics cards
function displaySummaryStats(summary) {
    const container = document.getElementById('summary_stats');
    
    const stats = [
        { icon: 'fas fa-leaf', label: 'Final LAI', value: summary.current_lai?.toFixed(2) || '0.00', color: 'success' },
        { icon: 'fas fa-weight', label: 'Total Biomass', value: `${summary.total_biomass_g?.toFixed(1) || '0.0'} g`, color: 'primary' },
        { icon: 'fas fa-tint', label: 'Water Use', value: `${summary.total_water_consumption_L?.toFixed(1) || '0.0'} L`, color: 'info' },
        { icon: 'fas fa-temperature-high', label: 'Avg Temp', value: `${summary.average_temperature?.toFixed(1) || '0.0'} °C`, color: 'warning' },
        { icon: 'fas fa-seedling', label: 'Growth Rate', value: `${summary.average_growth_rate?.toFixed(3) || '0.000'} g/day`, color: 'secondary' },
        { icon: 'fas fa-chart-line', label: 'WUE', value: `${summary.average_water_use_efficiency?.toFixed(2) || '0.00'} kg/m³`, color: 'dark' }
    ];
    
    container.innerHTML = '';
    
    stats.forEach(stat => {
        const statCard = document.createElement('div');
        statCard.className = 'col-md-2 col-6';
        
        statCard.innerHTML = `
            <div class="stat-card">
                <div class="stat-icon text-${stat.color}">
                    <i class="${stat.icon}"></i>
                </div>
                <div class="stat-value text-${stat.color}">${stat.value}</div>
                <div class="stat-label">${stat.label}</div>
            </div>
        `;
        
        container.appendChild(statCard);
    });
}

// Display charts
function displayCharts(results) {
    const dailyData = results.daily_results;
    
    // Extract data arrays
    const days = dailyData.map(d => d.day);
    const biomassData = dailyData.map(d => d.biomass?.total_biomass || 0);
    const laiData = dailyData.map(d => d.canopy?.lai || 0);
    const tempData = dailyData.map(d => d.basic?.temperature || 0);
    const photosynthesisData = dailyData.map(d => d.physiology?.photosynthesis_rate || 0);
    
    // Create biomass chart
    createChart('biomass_chart', 'Total Biomass Growth', {
        labels: days,
        datasets: [{
            label: 'Biomass (g)',
            data: biomassData,
            borderColor: 'rgb(40, 167, 69)',
            backgroundColor: 'rgba(40, 167, 69, 0.1)',
            tension: 0.4
        }]
    });
    
    // Create LAI chart
    createChart('lai_chart', 'Leaf Area Index Development', {
        labels: days,
        datasets: [{
            label: 'LAI',
            data: laiData,
            borderColor: 'rgb(13, 110, 253)',
            backgroundColor: 'rgba(13, 110, 253, 0.1)',
            tension: 0.4
        }]
    });
    
    // Create environment chart
    createChart('environment_chart', 'Environmental Conditions', {
        labels: days,
        datasets: [
            {
                label: 'Temperature (°C)',
                data: tempData,
                borderColor: 'rgb(255, 193, 7)',
                backgroundColor: 'rgba(255, 193, 7, 0.1)',
                yAxisID: 'y',
                tension: 0.4
            },
            {
                label: 'Photosynthesis Rate',
                data: photosynthesisData,
                borderColor: 'rgb(25, 135, 84)',
                backgroundColor: 'rgba(25, 135, 84, 0.1)',
                yAxisID: 'y1',
                tension: 0.4
            }
        ]
    }, {
        scales: {
            y: {
                type: 'linear',
                display: true,
                position: 'left',
            },
            y1: {
                type: 'linear',
                display: true,
                position: 'right',
                grid: {
                    drawOnChartArea: false,
                },
            },
        }
    });

    // Create detailed charts for specific tabs
    createDetailedBiomassCharts(dailyData, days);
    createDetailedPhysiologyCharts(dailyData, days);
    createDetailedStressCharts(dailyData, days);
    createDetailedGeneticsCharts(dailyData, days);
}

// Create detailed biomass charts
function createDetailedBiomassCharts(dailyData, days) {
    // Extract biomass component data
    const leafBiomass = dailyData.map(d => d.biomass?.leaf_biomass || 0);
    const stemBiomass = dailyData.map(d => d.biomass?.stem_biomass || 0);
    const rootBiomass = dailyData.map(d => d.biomass?.root_biomass || 0);
    const growthRate = dailyData.map(d => d.biomass?.daily_growth_rate || 0);
    
    // Biomass components chart
    createChart('biomass_components_chart', 'Biomass Components', {
        labels: days,
        datasets: [
            {
                label: 'Leaf Biomass (g)',
                data: leafBiomass,
                borderColor: 'rgb(40, 167, 69)',
                backgroundColor: 'rgba(40, 167, 69, 0.1)',
                tension: 0.4
            },
            {
                label: 'Stem Biomass (g)',
                data: stemBiomass,
                borderColor: 'rgb(139, 69, 19)',
                backgroundColor: 'rgba(139, 69, 19, 0.1)',
                tension: 0.4
            },
            {
                label: 'Root Biomass (g)',
                data: rootBiomass,
                borderColor: 'rgb(160, 82, 45)',
                backgroundColor: 'rgba(160, 82, 45, 0.1)',
                tension: 0.4
            }
        ]
    });
    
    // Growth rate chart
    createChart('growth_rate_chart', 'Daily Growth Rate', {
        labels: days,
        datasets: [{
            label: 'Growth Rate (g/day)',
            data: growthRate,
            borderColor: 'rgb(255, 99, 132)',
            backgroundColor: 'rgba(255, 99, 132, 0.1)',
            tension: 0.4
        }]
    });
}

// Create detailed physiology charts
function createDetailedPhysiologyCharts(dailyData, days) {
    // Extract physiology data
    const photosynthesis = dailyData.map(d => d.physiology?.photosynthesis_rate || 0);
    const respiration = dailyData.map(d => d.physiology?.respiration_rate || 0);
    const netAssimilation = dailyData.map(d => d.physiology?.net_assimilation || 0);
    const nitrogenUptake = dailyData.map(d => d.nitrogen?.nitrogen_uptake_mg || 0);
    const leafNitrogen = dailyData.map(d => d.nitrogen?.leaf_nitrogen_conc || 0);
    
    // Photosynthesis vs respiration chart
    createChart('photosynthesis_chart', 'Photosynthesis & Respiration', {
        labels: days,
        datasets: [
            {
                label: 'Photosynthesis Rate',
                data: photosynthesis,
                borderColor: 'rgb(34, 139, 34)',
                backgroundColor: 'rgba(34, 139, 34, 0.1)',
                tension: 0.4
            },
            {
                label: 'Respiration Rate',
                data: respiration,
                borderColor: 'rgb(220, 20, 60)',
                backgroundColor: 'rgba(220, 20, 60, 0.1)',
                tension: 0.4
            },
            {
                label: 'Net Assimilation',
                data: netAssimilation,
                borderColor: 'rgb(0, 100, 0)',
                backgroundColor: 'rgba(0, 100, 0, 0.1)',
                tension: 0.4
            }
        ]
    });
    
    // Nitrogen dynamics chart
    createChart('nitrogen_chart', 'Nitrogen Dynamics', {
        labels: days,
        datasets: [
            {
                label: 'N Uptake (mg/day)',
                data: nitrogenUptake,
                borderColor: 'rgb(54, 162, 235)',
                backgroundColor: 'rgba(54, 162, 235, 0.1)',
                yAxisID: 'y',
                tension: 0.4
            },
            {
                label: 'Leaf N Concentration (%)',
                data: leafNitrogen,
                borderColor: 'rgb(153, 102, 255)',
                backgroundColor: 'rgba(153, 102, 255, 0.1)',
                yAxisID: 'y1',
                tension: 0.4
            }
        ]
    }, {
        scales: {
            y: {
                type: 'linear',
                display: true,
                position: 'left',
            },
            y1: {
                type: 'linear',
                display: true,
                position: 'right',
                grid: {
                    drawOnChartArea: false,
                },
            },
        }
    });
}

// Create detailed stress charts
function createDetailedStressCharts(dailyData, days) {
    // Extract stress data
    const tempStress = dailyData.map(d => d.stress?.temperature_stress || 0);
    const waterStress = dailyData.map(d => d.stress?.water_stress || 1);
    const nutrientStress = dailyData.map(d => d.stress?.nutrient_stress || 1);
    const integratedStress = dailyData.map(d => d.stress?.integrated_stress || 1);
    
    // Convert stress factors to percentage for consistent display
    // All stress values: 0.0 = maximum stress, 1.0 = no stress
    // Display as stress level: 0% = no stress, 100% = maximum stress
    const tempStressPercent = tempStress.map(s => s * 100); // Temperature stress is already stress level (0-1)
    const waterStressPercent = waterStress.map(s => (1 - s) * 100); // Convert stress factor to stress level
    const nutrientStressPercent = nutrientStress.map(s => (1 - s) * 100); // Convert stress factor to stress level  
    const integratedStressPercent = integratedStress.map(s => (1 - s) * 100); // Convert stress factor to stress level
    
    createChart('stress_factors_chart', 'Stress Factors (%)', {
        labels: days,
        datasets: [
            {
                label: 'Temperature Stress (%)',
                data: tempStressPercent,
                borderColor: 'rgb(255, 99, 132)',
                backgroundColor: 'rgba(255, 99, 132, 0.1)',
                tension: 0.4
            },
            {
                label: 'Water Stress (%)',
                data: waterStressPercent,
                borderColor: 'rgb(54, 162, 235)',
                backgroundColor: 'rgba(54, 162, 235, 0.1)',
                tension: 0.4
            },
            {
                label: 'Nutrient Stress (%)',
                data: nutrientStressPercent,
                borderColor: 'rgb(255, 205, 86)',
                backgroundColor: 'rgba(255, 205, 86, 0.1)',
                tension: 0.4
            },
            {
                label: 'Integrated Stress (%)',
                data: integratedStressPercent,
                borderColor: 'rgb(75, 192, 192)',
                backgroundColor: 'rgba(75, 192, 192, 0.1)',
                tension: 0.4,
                borderWidth: 3
            }
        ]
    }, {
        scales: {
            y: {
                beginAtZero: true,
                max: 100,
                title: {
                    display: true,
                    text: 'Stress Level (%)'
                }
            }
        }
    });
}

// Create detailed genetics charts
function createDetailedGeneticsCharts(dailyData, days) {
    // Extract genetics data
    const cultivarAdaptation = dailyData.map(d => d.genetics?.cultivar_adaptation_index || 1);
    const yieldPotential = dailyData.map(d => d.genetics?.yield_potential || 1);
    const photosynthesisCapacity = dailyData.map(d => d.genetics?.photosynthesis_capacity || 1);
    
    createChart('genetics_chart', 'Genetic Performance Factors', {
        labels: days,
        datasets: [
            {
                label: 'Cultivar Adaptation Index',
                data: cultivarAdaptation,
                borderColor: 'rgb(138, 43, 226)',
                backgroundColor: 'rgba(138, 43, 226, 0.1)',
                tension: 0.4
            },
            {
                label: 'Yield Potential',
                data: yieldPotential,
                borderColor: 'rgb(255, 140, 0)',
                backgroundColor: 'rgba(255, 140, 0, 0.1)',
                tension: 0.4
            },
            {
                label: 'Photosynthesis Capacity',
                data: photosynthesisCapacity,
                borderColor: 'rgb(50, 205, 50)',
                backgroundColor: 'rgba(50, 205, 50, 0.1)',
                tension: 0.4
            }
        ]
    }, {
        scales: {
            y: {
                beginAtZero: false,
                min: 0.5,
                max: 1.5,
                title: {
                    display: true,
                    text: 'Factor Value'
                }
            }
        }
    });
}

// Create individual chart
function createChart(canvasId, title, data, options = {}) {
    const ctx = document.getElementById(canvasId);
    
    // Destroy existing chart if it exists
    if (currentCharts[canvasId]) {
        currentCharts[canvasId].destroy();
    }
    
    const defaultOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            title: {
                display: true,
                text: title,
                font: {
                    size: 14,
                    weight: 'bold'
                }
            },
            legend: {
                display: true,
                position: 'top'
            }
        },
        scales: {
            x: {
                title: {
                    display: true,
                    text: 'Day'
                }
            },
            y: {
                title: {
                    display: true,
                    text: 'Value'
                }
            }
        }
    };
    
    const mergedOptions = { ...defaultOptions, ...options };
    
    currentCharts[canvasId] = new Chart(ctx, {
        type: 'line',
        data: data,
        options: mergedOptions
    });
}

// Display detailed data table
function displayDetailedData(dailyResults) {
    const container = document.getElementById('detailed_data_table');
    
    if (!dailyResults || dailyResults.length === 0) {
        container.innerHTML = '<p class="text-muted">No detailed data available</p>';
        return;
    }
    
    // Create comprehensive detailed data table
    let tableHtml = `
        <div class="data-table table-responsive">
            <table class="table table-striped table-hover table-sm">
                <thead class="table-dark">
                    <tr>
                        <th>Day</th>
                        <th>Date</th>
                        <th>Temp (°C)</th>
                        <th>Humidity (%)</th>
                        <th>VPD (kPa)</th>
                        <th>CO₂ (ppm)</th>
                        <th>Total Biomass (g)</th>
                        <th>Leaf Biomass (g)</th>
                        <th>Stem Biomass (g)</th>
                        <th>Root Biomass (g)</th>
                        <th>LAI</th>
                        <th>Height (cm)</th>
                        <th>Growth Stage</th>
                        <th>Photo Rate (μmol/m²/s)</th>
                        <th>Respiration (μmol/m²/s)</th>
                        <th>Net Assim (μmol/m²/s)</th>
                        <th>Water Uptake (L)</th>
                        <th>N Uptake (mg)</th>
                        <th>N Conc (%)</th>
                        <th>Temp Stress</th>
                        <th>Water Stress</th>
                        <th>Nutrient Stress</th>
                        <th>Integrated Stress</th>
                        <th>Genetic Index</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    dailyResults.forEach(day => {
        tableHtml += `
            <tr>
                <td><strong>${day.day}</strong></td>
                <td>${day.date}</td>
                <td>${day.basic?.temperature?.toFixed(1) || 'N/A'}</td>
                <td>${day.basic?.humidity?.toFixed(1) || 'N/A'}</td>
                <td>${day.basic?.vpd?.toFixed(2) || 'N/A'}</td>
                <td>${day.basic?.co2_concentration?.toFixed(0) || '400'}</td>
                <td><span class="text-success"><strong>${day.biomass?.total_biomass?.toFixed(2) || '0.00'}</strong></span></td>
                <td>${day.biomass?.leaf_biomass?.toFixed(2) || '0.00'}</td>
                <td>${day.biomass?.stem_biomass?.toFixed(2) || '0.00'}</td>
                <td>${day.biomass?.root_biomass?.toFixed(2) || '0.00'}</td>
                <td><span class="text-primary">${day.canopy?.lai?.toFixed(3) || '0.000'}</span></td>
                <td>${day.canopy?.height_cm?.toFixed(1) || '0.0'}</td>
                <td><span class="badge bg-info">${day.phenology?.growth_stage || 'VE'}</span></td>
                <td>${day.physiology?.photosynthesis_rate?.toFixed(4) || '0.0000'}</td>
                <td>${day.physiology?.respiration_rate?.toFixed(4) || '0.0000'}</td>
                <td>${day.physiology?.net_assimilation?.toFixed(4) || '0.0000'}</td>
                <td>${day.water?.total_uptake_L?.toFixed(3) || '0.000'}</td>
                <td>${day.nitrogen?.nitrogen_uptake_mg?.toFixed(2) || '0.00'}</td>
                <td>${day.nitrogen?.leaf_nitrogen_conc?.toFixed(2) || '0.00'}</td>
                <td><span class="stress-indicator" style="background-color: rgba(255,99,132,${(day.stress?.temperature_stress || 0) * 0.5})">${(day.stress?.temperature_stress || 0).toFixed(3)}</span></td>
                <td><span class="stress-indicator" style="background-color: rgba(54,162,235,${(1 - (day.stress?.water_stress || 1)) * 0.5})">${(day.stress?.water_stress || 1).toFixed(3)}</span></td>
                <td><span class="stress-indicator" style="background-color: rgba(255,205,86,${(1 - (day.stress?.nutrient_stress || 1)) * 0.5})">${(day.stress?.nutrient_stress || 1).toFixed(3)}</span></td>
                <td><span class="text-${day.stress?.integrated_stress > 0.8 ? 'success' : day.stress?.integrated_stress > 0.6 ? 'warning' : 'danger'}">${(day.stress?.integrated_stress || 1).toFixed(3)}</span></td>
                <td>${day.genetics?.cultivar_adaptation_index?.toFixed(3) || '1.000'}</td>
            </tr>
        `;
    });
    
    tableHtml += `
                </tbody>
            </table>
        </div>
        
        <!-- Data Export Summary -->
        <div class="mt-3 d-flex justify-content-between align-items-center">
            <small class="text-muted">
                <i class="fas fa-info-circle"></i> 
                Showing ${dailyResults.length} days of detailed simulation results. 
                Use export buttons above to download data.
            </small>
            <div class="data-stats">
                <span class="badge bg-success me-2">Total Days: ${dailyResults.length}</span>
                <span class="badge bg-primary me-2">Data Points: ${dailyResults.length * 24}</span>
                <span class="badge bg-info">Models: 11 Integrated</span>
            </div>
        </div>
    `;
    
    container.innerHTML = tableHtml;
}

// Display genetics information
function displayGeneticsInfo(results) {
    const container = document.getElementById('genetics_info');
    const metadata = results.metadata;
    const finalDay = results.daily_results[results.daily_results.length - 1];
    
    // Get genetic data from final day
    const genetics = finalDay.genetics || {};
    
    container.innerHTML = `
        <div class="genetics-info">
            <h6 class="mb-3"><i class="fas fa-dna"></i> Cultivar Genetic Profile</h6>
            
            <div class="mb-3">
                <div class="genetics-coefficient">
                    <span class="coefficient-name">Cultivar ID</span>
                    <span class="coefficient-value">${metadata.cultivar_id}</span>
                </div>
                <div class="genetics-coefficient">
                    <span class="coefficient-name">Cultivar Name</span>
                    <span class="coefficient-value">${metadata.cultivar_name}</span>
                </div>
            </div>
            
            <h6 class="text-primary mb-2">Performance Indices</h6>
            <div class="genetics-coefficient">
                <span class="coefficient-name">Adaptation Index</span>
                <span class="coefficient-value">${genetics.cultivar_adaptation_index?.toFixed(3) || '1.000'}</span>
            </div>
            <div class="genetics-coefficient">
                <span class="coefficient-name">Yield Potential</span>
                <span class="coefficient-value">${genetics.yield_potential?.toFixed(3) || '1.000'}</span>
            </div>
            <div class="genetics-coefficient">
                <span class="coefficient-name">Photosynthetic Capacity</span>
                <span class="coefficient-value">${genetics.photosynthesis_capacity?.toFixed(3) || '1.000'}</span>
            </div>
            
            <h6 class="text-primary mb-2 mt-3">DSSAT-Style Coefficients</h6>
            <div class="genetics-coefficient">
                <span class="coefficient-name">LFMAX (Photosyn. Rate)</span>
                <span class="coefficient-value">1.20</span>
            </div>
            <div class="genetics-coefficient">
                <span class="coefficient-name">SLAVR (Specific Leaf Area)</span>
                <span class="coefficient-value">180 cm²/g</span>
            </div>
            <div class="genetics-coefficient">
                <span class="coefficient-name">EC_TOLERANCE</span>
                <span class="coefficient-value">1.3 dS/m</span>
            </div>
            <div class="genetics-coefficient">
                <span class="coefficient-name">NITRATE_EFFICIENCY</span>
                <span class="coefficient-value">0.85</span>
            </div>
            <div class="genetics-coefficient">
                <span class="coefficient-name">ROOT_ACTIVITY</span>
                <span class="coefficient-value">1.0</span>
            </div>
            
            <div class="mt-3">
                <h6 class="text-muted mb-2">Integrated Models (${metadata.models_used?.length || 0})</h6>
                <div class="row">
                    <div class="col-6">
                        <ul class="list-unstyled small">
                            <li><i class="fas fa-check text-success me-2"></i>Genetic Parameters</li>
                            <li><i class="fas fa-check text-success me-2"></i>Phenology Model</li>
                            <li><i class="fas fa-check text-success me-2"></i>FvCB Photosynthesis</li>
                            <li><i class="fas fa-check text-success me-2"></i>Respiration Model</li>
                            <li><i class="fas fa-check text-success me-2"></i>Senescence Model</li>
                            <li><i class="fas fa-check text-success me-2"></i>Canopy Architecture</li>
                        </ul>
                    </div>
                    <div class="col-6">
                        <ul class="list-unstyled small">
                            <li><i class="fas fa-check text-success me-2"></i>Nitrogen Balance</li>
                            <li><i class="fas fa-check text-success me-2"></i>Nutrient Mobility</li>
                            <li><i class="fas fa-check text-success me-2"></i>Stress Integration</li>
                            <li><i class="fas fa-check text-success me-2"></i>Temperature Stress</li>
                            <li><i class="fas fa-check text-success me-2"></i>Root Architecture</li>
                            <li><i class="fas fa-check text-success me-2"></i>Environmental Control</li>
                        </ul>
                    </div>
                </div>
            </div>
            
            <div class="mt-3 p-2 bg-light rounded">
                <small class="text-muted">
                    <strong>Simulation Type:</strong> ${metadata.simulation_type}<br>
                    <strong>Total Duration:</strong> ${metadata.total_days} days<br>
                    <strong>Research Grade:</strong> Advanced CROPGRO modeling
                </small>
            </div>
        </div>
    `;
}

// Export results to different formats
async function exportResults(format) {
    if (!currentResults) {
        showAlert('No results to export - run a simulation first', 'warning');
        return;
    }
    
    try {
        if (format === 'csv') {
            exportToCSV();
        } else if (format === 'json') {
            exportToJSON();
        }
        
        showAlert(`Results exported as ${format.toUpperCase()}`, 'success');
    } catch (error) {
        console.error('Export error:', error);
        showAlert(`Export failed: ${error.message}`, 'danger');
    }
}

// Export to CSV
function exportToCSV() {
    const dailyData = currentResults.daily_results;
    
    // Create comprehensive CSV header
    let csvContent = 'Day,Date,Temperature_C,Humidity_Percent,VPD_kPa,CO2_ppm,Total_Biomass_g,Leaf_Biomass_g,Stem_Biomass_g,Root_Biomass_g,LAI,Height_cm,Growth_Stage,Photosynthesis_Rate,Respiration_Rate,Net_Assimilation,Water_Uptake_L,N_Uptake_mg,N_Concentration_Percent,Temperature_Stress,Water_Stress,Nutrient_Stress,Integrated_Stress,Genetic_Index\n';
    
    // Add data rows with all detailed columns
    dailyData.forEach(day => {
        const row = [
            day.day,
            day.date,
            day.basic?.temperature?.toFixed(2) || '',
            day.basic?.humidity?.toFixed(2) || '',
            day.basic?.vpd?.toFixed(3) || '',
            day.basic?.co2_concentration?.toFixed(0) || '',
            day.biomass?.total_biomass?.toFixed(3) || '',
            day.biomass?.leaf_biomass?.toFixed(3) || '',
            day.biomass?.stem_biomass?.toFixed(3) || '',
            day.biomass?.root_biomass?.toFixed(3) || '',
            day.canopy?.lai?.toFixed(4) || '',
            day.canopy?.height_cm?.toFixed(2) || '',
            day.phenology?.growth_stage || '',
            day.physiology?.photosynthesis_rate?.toFixed(6) || '',
            day.physiology?.respiration_rate?.toFixed(6) || '',
            day.physiology?.net_assimilation?.toFixed(6) || '',
            day.water?.total_uptake_L?.toFixed(4) || '',
            day.nitrogen?.nitrogen_uptake_mg?.toFixed(3) || '',
            day.nitrogen?.leaf_nitrogen_conc?.toFixed(3) || '',
            day.stress?.temperature_stress?.toFixed(4) || '',
            day.stress?.water_stress?.toFixed(4) || '',
            day.stress?.nutrient_stress?.toFixed(4) || '',
            day.stress?.integrated_stress?.toFixed(4) || '',
            day.genetics?.cultivar_adaptation_index?.toFixed(4) || ''
        ];
        csvContent += row.join(',') + '\n';
    });
    
    // Download file
    downloadFile('cropgro_results.csv', csvContent, 'text/csv');
}

// Export to JSON
function exportToJSON() {
    const jsonContent = JSON.stringify(currentResults, null, 2);
    downloadFile('cropgro_results.json', jsonContent, 'application/json');
}

// Download file helper
function downloadFile(filename, content, contentType) {
    const blob = new Blob([content], { type: contentType });
    const url = URL.createObjectURL(blob);
    
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.style.display = 'none';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    URL.revokeObjectURL(url);
}

// Show alert messages
function showAlert(message, type = 'info') {
    // Remove existing alerts
    const existingAlerts = document.querySelectorAll('.alert');
    existingAlerts.forEach(alert => alert.remove());
    
    // Create new alert
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alert.style.cssText = 'top: 20px; right: 20px; z-index: 9999; max-width: 400px;';
    
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alert);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        if (alert && alert.parentNode) {
            alert.remove();
        }
    }, 5000);
}

// Reset form to defaults
function loadDefaults() {
    // Reset all form fields
    document.getElementById('cultivar_id').value = 'HYDRO_001';
    document.getElementById('simulation_days').value = 14;
    
    // Reset weather type
    document.getElementById('weather_type').value = 'generate';
    toggleWeatherInputs();
    
    // Clear custom weather days
    document.getElementById('custom_weather_days').innerHTML = '';
    
    // Reload default values
    setTimeout(() => {
        loadDefaults();
    }, 100);
    
    showAlert('Default values loaded', 'info');
}

// Global error handler
window.addEventListener('error', function(event) {
    console.error('Global error:', event.error);
    showAlert('An unexpected error occurred', 'danger');
});

// Console welcome message
console.log(`
🌱 CROPGRO Hydroponic Simulator - Web UI
=========================================
✅ Advanced crop modeling system ready
🔬 11+ integrated CROPGRO models
🌡️  Environmental control & stress factors
🧬 Genetic parameters & G×E interactions
📊 Comprehensive scientific outputs

Ready to simulate!
`);