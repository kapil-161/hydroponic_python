#!/usr/bin/env python3
"""
Hydroponic Research Framework Dashboard
======================================

A professional dashboard for visualizing and analyzing hydroponic simulation results.
This dashboard provides interactive visualizations, key metrics, and correlation analyses
to support research and decision-making in hydroponic systems.
"""

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import streamlit as st
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# Page configuration for a professional look
st.set_page_config(
    page_title="Hydroponic Research Dashboard",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for a clean, modern, and professional interface
st.markdown("""
<style>
    /* Import Google Fonts for professional typography */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Define color variables for a consistent, professional theme */
    :root {
        --primary-blue: #2563EB;
        --primary-blue-light: #3B82F6;
        --primary-blue-dark: #1D4ED8;
        --secondary-green: #10B981;
        --secondary-green-light: #34D399;
        --accent-amber: #F59E0B;
        --accent-amber-light: #FBBF24;
        --background: #F5F7FA;
        --text-primary: #111827;
        --text-secondary: #6B7280;
        --border: #E5E7EB;
        --surface: #FFFFFF;
        --surface-hover: #F9FAFB;
    }
    
    /* Global styles for consistency */
    .main .block-container {
        background: var(--background);
        min-height: 100vh;
    }
    
    .stApp {
        background: var(--background);
    }
    
    /* Ensure text is readable (black) while handling dropdowns */
    * {
        color: #000000 !important;
    }
    
    /* Specific overrides for dropdowns and selects */
    .stSelectbox [data-baseweb="select"] > div,
    .stMultiSelect [data-baseweb="select"] > div,
    .stSelectbox [data-baseweb="select"] span,
    .stMultiSelect [data-baseweb="select"] span,
    .stSelectbox [data-baseweb="select"] div[role="button"],
    .stMultiSelect [data-baseweb="select"] div[role="button"] {
        color: #ffffff !important;
    }
    
    [data-baseweb="menu"] li,
    [data-baseweb="menu"] div,
    [data-baseweb="popover"] li,
    [data-baseweb="popover"] div {
        color: #000000 !important;
    }
    
    /* Header styles */
    .main-header {
        font-family: 'Inter', sans-serif;
        font-size: 3rem;
        font-weight: 700;
        color: var(--text-primary) !important;
        text-align: center;
        margin-bottom: 2rem;
        text-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .section-header {
        font-family: 'Inter', sans-serif;
        font-size: 1.75rem;
        font-weight: 600;
        color: var(--text-primary) !important;
        margin: 2rem 0 1rem 0;
        padding: 0.75rem 0;
        border-bottom: 3px solid var(--primary-blue);
        position: relative;
    }
    
    .section-header::before {
        content: '';
        position: absolute;
        bottom: -3px;
        left: 0;
        width: 50px;
        height: 3px;
        background: var(--secondary-green);
    }
    
    /* Metric cards for KPIs */
    .stMetric {
        background: var(--surface);
        padding: 1.25rem;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        border-left: 4px solid var(--primary-blue);
        transition: all 0.3s ease;
        font-family: 'Inter', sans-serif;
        border: 1px solid var(--border);
    }
    
    .stMetric:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
    }
    
    .stMetric [data-testid="metric-container"] {
        gap: 0.5rem;
    }
    
    .stMetric [data-testid="metric-value"] {
        font-size: 1.5rem;
        font-weight: 700;
        color: var(--text-primary) !important;
    }
    
    .stMetric [data-testid="metric-label"] {
        font-size: 0.875rem;
        font-weight: 500;
        color: var(--text-secondary) !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* Tabs for navigation */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        padding: 0.5rem;
        background: var(--surface);
        border-radius: 12px;
        border: 1px solid var(--border);
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 48px;
        white-space: nowrap;
        background: transparent;
        border-radius: 8px;
        padding: 0 1.5rem;
        font-family: 'Inter', sans-serif;
        font-weight: 500;
        font-size: 0.875rem;
        color: var(--text-secondary) !important;
        transition: all 0.3s ease;
        border: 1px solid transparent;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background: var(--surface-hover);
        color: var(--text-primary) !important;
        border-color: var(--border);
    }
    
    .stTabs [aria-selected="true"] {
        background: var(--primary-blue);
        color: white !important;
        border-color: var(--primary-blue);
        box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.3);
    }
    
    /* Buttons for actions */
    .stButton > button {
        background: var(--primary-blue);
        color: white !important;
        border: none;
        border-radius: 8px;
        padding: 0.75rem 1.5rem;
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        font-size: 0.875rem;
        transition: all 0.3s ease;
        box-shadow: 0 2px 4px rgba(37, 99, 235, 0.2);
    }
    
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(37, 99, 235, 0.3);
        background: var(--primary-blue-dark);
        color: white !important;
    }
    
    /* Form elements like selectboxes */
    .stSelectbox > div > div,
    .stMultiSelect > div > div {
        background: var(--surface);
        border-radius: 8px;
        border: 1px solid var(--border);
        transition: all 0.3s ease;
    }
    
    .stSelectbox > div > div:hover,
    .stMultiSelect > div > div:hover {
        border-color: var(--primary-blue);
        box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
        background: var(--surface-hover);
    }
    
    /* Dropdown text overrides */
    .stSelectbox [data-baseweb="select"] > div[role="button"],
    .stMultiSelect [data-baseweb="select"] > div[role="button"] {
        color: #000000 !important;
    }
    
    [data-baseweb="menu"] {
        background: white !important;
    }
    
    [data-baseweb="menu"] li {
        color: #000000 !important;
    }
    
    [data-baseweb="menu"] li:hover {
        background: #f0fdf4 !important;
        color: #000000 !important;
    }
    
    /* Ensure selected/highlighted option has contrasting colors */
    [data-baseweb="menu"] [aria-selected="true"],
    [data-baseweb="menu"] li[aria-selected="true"],
    [data-baseweb="menu"] li[data-selected="true"],
    [data-baseweb="menu"] li:active {
        background: var(--primary-blue) !important;
        color: #ffffff !important;
    }

    /* Keyboard/hover focus states for options */
    [data-baseweb="menu"] [role="option"][data-highlighted="true"],
    [data-baseweb="menu"] [role="option"]:hover,
    [data-baseweb="menu"] li:focus {
        background: var(--primary-blue) !important;
        color: #ffffff !important;
        outline: none !important;
    }

    /* Ensure popover menus behave the same */
    [data-baseweb="popover"] [role="option"][data-highlighted="true"],
    [data-baseweb="popover"] [role="option"]:hover {
        background: var(--primary-blue) !important;
        color: #ffffff !important;
    }
    
    /* Info, warning, success boxes */
    .info-box {
        background: #EFF6FF;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid var(--primary-blue);
        margin: 1rem 0;
        font-family: 'Inter', sans-serif;
        color: var(--text-primary) !important;
    }
    
    .warning-box {
        background: #FEF3C7;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid var(--accent-amber);
        margin: 1rem 0;
        font-family: 'Inter', sans-serif;
        color: var(--text-primary) !important;
    }
    
    .success-box {
        background: #D1FAE5;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid var(--secondary-green);
        margin: 1rem 0;
        font-family: 'Inter', sans-serif;
        color: var(--text-primary) !important;
    }
    
    /* Sidebar styling */
    .sidebar .sidebar-content {
        background: var(--surface);
    }
    
    /* Data tables */
    .stDataFrame {
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        border: 1px solid var(--border);
        background: var(--surface);
    }
    
    /* Chart containers for visual separation */
    .chart-container {
        background: var(--surface);
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        margin: 1rem 0;
        border: 1px solid var(--border);
    }
    
    /* Scrollbar for better UX */
    ::-webkit-scrollbar {
        width: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: var(--background);
    }
    
    ::-webkit-scrollbar-thumb {
        background: var(--text-secondary);
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: var(--text-primary);
    }
    
    /* Focus states for accessibility */
    .stSelectbox > div > div:focus-within,
    .stMultiSelect > div > div:focus-within {
        border-color: var(--secondary-green);
        box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.1);
    }
</style>
""", unsafe_allow_html=True)

def get_color_palette():
    """
    Returns a consistent color palette for charts.
    The palette is designed for professional, distinguishable colors.
    """
    return [
        '#2563EB',  # Blue
        '#10B981',  # Green
        '#F59E0B',  # Amber
        '#8B5CF6',  # Violet
        '#EF4444',  # Red
        '#06B6D4',  # Cyan
        '#84CC16',  # Lime
        '#F97316',  # Orange
        '#EC4899',  # Pink
        '#6B7280'   # Gray
    ]

def update_chart_layout(fig, title, x_title, y_title, height=500):
    """
    Updates the layout of a Plotly figure with a professional theme.
    
    Parameters:
    - fig: Plotly figure object
    - title: Chart title
    - x_title: X-axis title
    - y_title: Y-axis title
    - height: Chart height (default: 500)
    
    Returns:
    - Updated Plotly figure
    """
    fig.update_layout(
        title=dict(text=title, font=dict(size=20, family='Inter', color='#111827')),
        height=height,
        plot_bgcolor='#F5F7FA',
        paper_bgcolor='#F5F7FA',
        font=dict(family='Inter', color='#111827'),
        hovermode='x unified',
        margin=dict(t=80, b=40, l=60, r=20),
        xaxis=dict(
            title=dict(text=x_title, font=dict(color='#111827')),
            tickfont=dict(color='#111827')
        ),
        yaxis=dict(
            title=dict(text=y_title, font=dict(color='#111827')),
            tickfont=dict(color='#111827')
        ),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=1.12,
            xanchor="center",
            x=0.5,
            bgcolor='rgba(255,255,255,0.95)',
            bordercolor='#E5E7EB',
            borderwidth=1,
            font=dict(color='#111827', size=12)
        ),
        showlegend=True
    )
    return fig

def load_data(file_path='output/simulation_results.csv'):
    """
    Loads simulation data from CSV, handles duplicate columns, and provides feedback.
    
    Parameters:
    - file_path: Path to the CSV file (default: 'output/simulation_results.csv')
    
    Returns:
    - pandas DataFrame or None if loading fails
    """
    try:
        data = pd.read_csv(file_path)
        
        # Handle duplicate columns
        if data.columns.duplicated().any():
            st.warning("⚠️ Duplicate column names detected. Automatically renaming duplicates.")
            cols = pd.Series(data.columns)
            for dup in cols[cols.duplicated()].unique():
                dup_indices = cols[cols == dup].index.values.tolist()
                cols[dup_indices] = [f"{dup}_{i}" if i > 0 else dup for i in range(len(dup_indices))]
            data.columns = cols
        
        st.success(f"✅ Successfully loaded {len(data):,} records spanning days {data['day'].min()} to {data['day'].max()}.")
        return data
    except FileNotFoundError:
        st.error(f"❌ File not found: {file_path}. Please ensure the simulation results CSV exists.")
        return None
    except Exception as e:
        st.error(f"❌ Error loading data: {str(e)}. Please check the file format and content.")
        return None

def create_summary_metrics(data):
    """Displays key performance indicators as metric cards."""
    st.markdown('<div class="section-header">📊 Key Performance Indicators</div>', unsafe_allow_html=True)
    
    cols = st.columns(4)
    
    metrics = [
        ("🌱 Total Biomass", 'biomass_allocation_simulator_total_biomass', 'biomass_allocation_simulator_daily_biomass_gain', "g", "g/day"),
        ("📈 Growth Stage", 'phenology_simulator_current_growth_stage', 'phenology_simulator_development_index', "", ""),
        ("🌿 Leaf Area Index", 'canopy_architecture_simulator_lai', None, "", " (Max)"),
        ("💧 Water Uptake", 'water_uptake_simulator_cumulative_water_uptake', 'water_uptake_simulator_daily_water_uptake', "L", "L/day")
    ]
    
    for col, (label, main_col, delta_col, unit, delta_unit) in zip(cols, metrics):
        with col:
            if main_col in data.columns:
                main_value = data[main_col].iloc[-1]
                try:
                    main_num = float(main_value)
                    value_str = f"{main_num:.2f}" + (f" {unit}" if unit else "")
                except ValueError:
                    value_str = str(main_value) + (f" {unit}" if unit else "")
                
                if delta_col:
                    delta_value = data[delta_col].iloc[-1] if delta_col in data.columns else 0
                    try:
                        delta_num = float(delta_value)
                        delta_str = f"{delta_num:.3f}" + (f" {delta_unit}" if delta_unit else "")
                    except ValueError:
                        delta_str = str(delta_value) + (f" {delta_unit}" if delta_unit else "")
                    st.metric(label, value_str, delta=delta_str)
                elif 'Max' in delta_unit:
                    max_value = data[main_col].max()
                    try:
                        main_num = float(main_value)
                        max_num = float(max_value)
                        st.metric(label, f"{main_num:.3f}" + (f" {unit}" if unit else ""), delta=f"Max: {max_num:.3f}")
                    except ValueError:
                        st.metric(label, str(main_value), delta="N/A")
                else:
                    st.metric(label, value_str)
            else:
                st.metric(label, "N/A")

def create_generic_time_series_chart(data, section_title, column_filter, default_vars_count=3, y_title="Value", height=500):
    """
    Generic function to create time series charts with variable selection and controls.
    
    Parameters:
    - data: pandas DataFrame
    - section_title: Title for the section
    - column_filter: Function to filter relevant columns (e.g., lambda col: 'biomass' in col.lower())
    - default_vars_count: Number of default variables to select
    - y_title: Y-axis title
    - height: Chart height
    
    Returns:
    - None (renders the chart in Streamlit)
    """
    st.markdown(f'<div class="section-header">{section_title}</div>', unsafe_allow_html=True)
    
    relevant_columns = [col for col in data.columns if column_filter(col)]
    
    if not relevant_columns:
        st.markdown('<div class="warning-box">⚠️ Relevant data not available for this section.</div>', unsafe_allow_html=True)
        return
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.markdown("#### 🎛️ Chart Controls")
        selected_vars = st.multiselect(
            "Select Variables:",
            options=relevant_columns,
            default=relevant_columns[:default_vars_count] if len(relevant_columns) >= default_vars_count else relevant_columns,
            help="Choose variables to visualize in the chart.",
            key=f"multiselect_vars_{section_title}"
        )
        
        chart_type = st.selectbox(
            "Chart Style:",
            ["Lines", "Markers", "Lines + Markers", "Area"],
            help="Select the visualization style for the data.",
            key=f"selectbox_chart_type_{section_title}"
        )
        
        smoothing = st.slider(
            "Smoothing Factor (Moving Average)",
            0,
            10,
            0,
            help="Apply smoothing to reduce noise in the data.",
            key=f"slider_smoothing_{section_title}"
        )
        
        show_trend = st.checkbox(
            "Show Trend Lines",
            value=False,
            help="Add linear trend lines to each series.",
            key=f"checkbox_trend_{section_title}"
        )
        
        show_secondary_y = st.checkbox(
            "Use Secondary Y-Axis",
            value=False,
            help="Plot additional variables on a secondary scale.",
            key=f"checkbox_secondary_y_{section_title}"
        )
    
    with col2:
        if selected_vars:
            fig = go.Figure()
            colors = get_color_palette()
            mode = {
                "Lines": 'lines',
                "Markers": 'markers',
                "Lines + Markers": 'lines+markers',
                "Area": 'lines'
            }[chart_type]
            fill = 'tonexty' if chart_type == "Area" else None
            
            for i, var in enumerate(selected_vars):
                y_data = data[var]
                if smoothing > 0:
                    y_data = y_data.rolling(window=smoothing + 1, center=True).mean()
                
                fig.add_trace(go.Scatter(
                    x=data['day'],
                    y=y_data,
                    mode=mode,
                    fill=fill if chart_type == "Area" and i == 0 else None,
                    name=var.replace('_simulator_', ' ').replace('_', ' ').title(),
                    line=dict(color=colors[i % len(colors)], width=3) if 'lines' in mode else None,
                    marker=dict(color=colors[i % len(colors)], size=8) if 'markers' in mode else None,
                    yaxis='y2' if show_secondary_y and i > 0 else 'y',
                    hovertemplate=f"<b>{var.replace('_', ' ').title()}</b><br>Day: %{{x}}<br>Value: %{{y:.3f}}<extra></extra>"
                ))
                
                if show_trend:
                    y_data_clean = y_data.dropna()
                    x_data = data['day'].loc[y_data_clean.index]
                    z = np.polyfit(x_data, y_data_clean, 1)
                    p = np.poly1d(z)
                    fig.add_trace(go.Scatter(
                        x=data['day'],
                        y=p(data['day']),
                        mode='lines',
                        name=f"Trend: {var.split('_')[-1].title()}",
                        line=dict(color=colors[i % len(colors)], dash='dash', width=2),
                        yaxis='y2' if show_secondary_y and i > 0 else 'y'
                    ))
            
            layout = {
                "xaxis_title": "Day",
                "yaxis_title": y_title,
                "height": height,
                "hovermode": 'x unified',
                "plot_bgcolor": '#F5F7FA',
                "paper_bgcolor": '#F5F7FA',
                "margin": dict(t=80, b=40, l=60, r=20),
                "legend": dict(
                    orientation="h",
                    yanchor="top",
                    y=1.12,
                    xanchor="center",
                    x=0.5,
                    bgcolor='rgba(255,255,255,0.95)',
                    bordercolor='#E5E7EB',
                    borderwidth=1,
                    font=dict(color='#111827', size=12)
                ),
                "showlegend": True
            }
            if show_secondary_y and len(selected_vars) > 1:
                layout["yaxis2"] = dict(
                    title=dict(text="Secondary Scale", font=dict(color='#111827')),
                    overlaying="y",
                    side="right",
                    tickfont=dict(color='#111827')
                )
            
            fig.update_layout(**layout)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.markdown('<div class="info-box">ℹ️ Select at least one variable to display the chart.</div>', unsafe_allow_html=True)

def create_correlation_heatmap(data, weather_filter, physiology_filter, max_vars=10):
    """
    Creates a correlation heatmap between weather and physiology variables.
    
    Parameters:
    - data: pandas DataFrame
    - weather_filter: Function to filter weather columns
    - physiology_filter: Function to filter physiology columns
    - max_vars: Maximum variables per category to display
    
    Returns:
    - None (renders the heatmap in Streamlit)
    """
    st.markdown('<div class="section-header">🌤️ Weather-Physiology Correlation Heatmap</div>', unsafe_allow_html=True)
    
    weather_vars = [col for col in data.select_dtypes(include=['float64', 'int64']).columns if weather_filter(col)][:max_vars]
    physiology_vars = [col for col in data.select_dtypes(include=['float64', 'int64']).columns if physiology_filter(col)][:max_vars]
    
    if not weather_vars or not physiology_vars:
        st.markdown('<div class="warning-box">⚠️ Insufficient data for correlation analysis.</div>', unsafe_allow_html=True)
        return
    
    all_vars = list(set(weather_vars + physiology_vars))
    corr_matrix = data[all_vars].corr()
    
    fig = go.Figure(data=go.Heatmap(
        z=corr_matrix.values,
        x=corr_matrix.columns,
        y=corr_matrix.index,
        colorscale=[[0, '#EF4444'], [0.5, '#F9FAFB'], [1, '#059669']],
        zmid=0,
        text=np.round(corr_matrix.values, 2),
        texttemplate="%{text}",
        textfont={"size": 10, "color": "#FFFFFF"},
        hoverongaps=False
    ))
    
    fig = update_chart_layout(fig, "Correlation Matrix", "Variables", "Variables", height=600)
    st.plotly_chart(fig, use_container_width=True)
    
    # Display top correlations
    st.markdown("#### 🔥 Top Correlations")
    corr_pairs = []
    for w in weather_vars:
        for p in physiology_vars:
            corr_val = corr_matrix.loc[w, p]
            if not np.isnan(corr_val):
                corr_pairs.append({
                    'Weather': w.replace('_', ' ').title(),
                    'Physiology': p.replace('_', ' ').title(),
                    'Correlation': corr_val
                })
    top_corrs = pd.DataFrame(corr_pairs).sort_values('Correlation', ascending=False).head(10)
    st.dataframe(top_corrs, use_container_width=True)

def create_growth_stage_timeline(data):
    """Creates a timeline visualization for growth stages."""
    st.markdown('<div class="section-header">📅 Growth Stage Timeline</div>', unsafe_allow_html=True)
    
    if 'phenology_simulator_current_growth_stage' not in data.columns:
        st.markdown('<div class="warning-box">⚠️ Growth stage data not available.</div>', unsafe_allow_html=True)
        return
    
    stages = data['phenology_simulator_current_growth_stage'].unique()
    fig = go.Figure()
    
    for i, stage in enumerate(stages):
        stage_data = data[data['phenology_simulator_current_growth_stage'] == stage]
        if not stage_data.empty:
            fig.add_trace(go.Scatter(
                x=stage_data['day'],
                y=[i] * len(stage_data),
                mode='markers+lines',
                name=str(stage),
                marker=dict(size=10, opacity=0.8),
                line=dict(width=2)
            ))
    
    fig = update_chart_layout(fig, "Growth Stages Over Time", "Day", "Stage", height=400)
    fig.update_yaxes(tickmode='array', tickvals=list(range(len(stages))), ticktext=[str(s) for s in stages])
    st.plotly_chart(fig, use_container_width=True)

def main():
    """Main function to orchestrate the dashboard."""
    st.markdown('<div class="main-header">🌱 Hydroponic Research Dashboard</div>', unsafe_allow_html=True)
    
    data = load_data()
    if data is None:
        return
    
    create_summary_metrics(data)
    
    tabs = st.tabs([
        "🌱 Growth & Biomass",
        "🌞 Photosynthesis & Respiration",
        "🌿 Canopy & Environment",
        "🌤️ Weather Correlations",
        "📊 Custom Analysis"
    ])
    
    with tabs[0]:
        create_generic_time_series_chart(
            data,
            "🌱 Biomass Growth Analysis",
            lambda col: 'biomass' in col.lower(),
            y_title="Biomass (g)"
        )
        create_growth_stage_timeline(data)
    
    with tabs[1]:
        create_generic_time_series_chart(
            data,
            "🌞 Photosynthesis Analysis",
            lambda col: 'photosynthesis' in col.lower(),
            y_title="Rate (μmol CO₂/m²/s)"
        )
        create_generic_time_series_chart(
            data,
            "🫁 Respiration Analysis",
            lambda col: 'respiration' in col.lower(),
            y_title="Rate (μmol CO₂/m²/s)"
        )
    
    with tabs[2]:
        create_generic_time_series_chart(
            data,
            "🌿 Canopy Architecture Analysis",
            lambda col: 'canopy' in col.lower()
        )
        create_generic_time_series_chart(
            data,
            "⚠️ Stress Levels Analysis",
            lambda col: 'stress' in col.lower()
        )
        create_generic_time_series_chart(
            data,
            "💧 Water Uptake Analysis",
            lambda col: 'water' in col.lower(),
            y_title="Water (L)"
        )
    
    with tabs[3]:
        create_generic_time_series_chart(
            data,
            "🌤️ Weather vs. Physiology (Custom Selection)",
            lambda col: True,  # Allow any for correlations, but user selects
            default_vars_count=2
        )
        create_correlation_heatmap(
            data,
            lambda col: any(term in col.lower() for term in ['temperature', 'humidity', 'light', 'co2', 'wind', 'pressure', 'precipitation']),
            lambda col: any(term in col.lower() for term in ['biomass', 'photosynthesis', 'respiration', 'lai', 'growth', 'stress', 'uptake'])
        )
    
    with tabs[4]:
        create_generic_time_series_chart(
            data,
            "📊 Custom Time Series Analysis",
            lambda col: data[col].dtype in ['float64', 'int64'] and col not in ['day', 'step', 'hour'],
            default_vars_count=5,
            height=600
        )
        
        st.markdown('<div class="section-header">🔍 Data Exploration</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 📈 Descriptive Statistics")
            st.dataframe(data.describe().round(3), use_container_width=True)
        with col2:
            st.markdown("#### 📊 Dataset Overview")
            st.write(f"**Records:** {len(data):,}")
            st.write(f"**Days:** {data['day'].min()} - {data['day'].max()}")
            st.write(f"**Columns:** {len(data.columns)}")
            st.write(f"**Numeric Columns:** {len(data.select_dtypes(include=['number']).columns)}")
    
    # Sidebar for quick actions and info
    with st.sidebar:
        st.markdown('<div class="section-header">📊 Simulation Overview</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="info-box">
        <strong>Period:</strong> Days {data['day'].min()} - {data['day'].max()}<br>
        <strong>Records:</strong> {len(data):,}<br>
        <strong>Data Points:</strong> {len(data) * len(data.columns):,}
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="section-header">🎛️ Actions</div>', unsafe_allow_html=True)
        if st.button("🔄 Refresh Dashboard", use_container_width=True):
            st.rerun()
        
        csv = data.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name="simulation_results.csv",
            mime="text/csv",
            use_container_width=True
        )
        
        st.markdown('<div class="section-header">📈 Quick Metrics</div>', unsafe_allow_html=True)
        if 'biomass_allocation_simulator_total_biomass' in data.columns:
            st.metric("Final Biomass", f"{data['biomass_allocation_simulator_total_biomass'].iloc[-1]:.2f} g")
        if 'canopy_architecture_simulator_lai' in data.columns:
            st.metric("Max LAI", f"{data['canopy_architecture_simulator_lai'].max():.3f}")
        if 'phenology_simulator_current_growth_stage' in data.columns:
            st.metric("Final Growth Stage", str(data['phenology_simulator_current_growth_stage'].iloc[-1]))

if __name__ == "__main__":
    main()