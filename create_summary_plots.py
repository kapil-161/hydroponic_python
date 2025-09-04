#!/usr/bin/env python3
"""
Create summary visualization plots for NFT lettuce analysis
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

def create_summary_plots():
    """Create key visualization plots"""
    df = pd.read_csv("/Users/kapilbhattarai/hydroponic_python/outputs/LET_EXP001_2024_results.csv")
    
    # Create figure with subplots
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle('NFT Lettuce Simulation - Key Metrics Analysis', fontsize=16, fontweight='bold')
    
    # Plot 1: Biomass progression
    axes[0,0].plot(df['Day'], df['Total_Biomass_g'], 'b-o', linewidth=2, markersize=4)
    axes[0,0].axhline(y=150, color='green', linestyle='--', alpha=0.7, label='Min Commercial (150g)')
    axes[0,0].axhline(y=300, color='green', linestyle='--', alpha=0.7, label='Max Commercial (300g)')
    axes[0,0].set_xlabel('Days After Transplant')
    axes[0,0].set_ylabel('Total Biomass (g)')
    axes[0,0].set_title('Total Biomass Progression')
    axes[0,0].legend()
    axes[0,0].grid(True, alpha=0.3)
    
    # Plot 2: Plant Height
    axes[0,1].plot(df['Day'], df['Plant_Height_cm'], 'g-o', linewidth=2, markersize=4)
    axes[0,1].axhline(y=12, color='orange', linestyle='--', alpha=0.7, label='Min Target (12cm)')
    axes[0,1].axhline(y=15, color='orange', linestyle='--', alpha=0.7, label='Max Target (15cm)')
    axes[0,1].set_xlabel('Days After Transplant')
    axes[0,1].set_ylabel('Plant Height (cm)')
    axes[0,1].set_title('Plant Height Development')
    axes[0,1].legend()
    axes[0,1].grid(True, alpha=0.3)
    
    # Plot 3: Water Use Efficiency
    axes[0,2].plot(df['Day'], df['WUE_kg_m3'], 'c-o', linewidth=2, markersize=4)
    axes[0,2].axhline(y=20, color='red', linestyle='--', alpha=0.7, label='Min Acceptable (20 kg/m³)')
    axes[0,2].set_xlabel('Days After Transplant')
    axes[0,2].set_ylabel('WUE (kg/m³)')
    axes[0,2].set_title('Water Use Efficiency')
    axes[0,2].legend()
    axes[0,2].grid(True, alpha=0.3)
    
    # Plot 4: Nutrient Concentrations
    nutrients = ['N-NO3_mg_L', 'P-PO4_mg_L', 'K_mg_L', 'Ca_mg_L', 'Mg_mg_L']
    colors = ['blue', 'red', 'green', 'orange', 'purple']
    
    for nutrient, color in zip(nutrients, colors):
        if nutrient in df.columns:
            axes[1,0].plot(df['Day'], df[nutrient], color=color, linewidth=2, label=nutrient.replace('_mg_L', ''))
    
    axes[1,0].set_xlabel('Days After Transplant')
    axes[1,0].set_ylabel('Concentration (mg/L)')
    axes[1,0].set_title('Nutrient Concentrations Over Time')
    axes[1,0].legend()
    axes[1,0].grid(True, alpha=0.3)
    
    # Plot 5: LAI Development
    axes[1,1].plot(df['Day'], df['LAI'], 'm-o', linewidth=2, markersize=4)
    axes[1,1].axhline(y=0.8, color='green', linestyle='--', alpha=0.7, label='Min Target (0.8)')
    axes[1,1].axhline(y=1.2, color='green', linestyle='--', alpha=0.7, label='Max Target (1.2)')
    axes[1,1].set_xlabel('Days After Transplant')
    axes[1,1].set_ylabel('Leaf Area Index')
    axes[1,1].set_title('LAI Development')
    axes[1,1].legend()
    axes[1,1].grid(True, alpha=0.3)
    
    # Plot 6: Daily Growth Rate
    axes[1,2].plot(df['Day'][1:], np.diff(df['Total_Biomass_g']), 'r-o', linewidth=2, markersize=4, label='Calculated')
    if 'Daily_Growth_Rate_g_day' in df.columns:
        axes[1,2].plot(df['Day'], df['Daily_Growth_Rate_g_day'], 'b--', linewidth=2, alpha=0.7, label='Reported')
    axes[1,2].set_xlabel('Days After Transplant')
    axes[1,2].set_ylabel('Daily Growth Rate (g/day)')
    axes[1,2].set_title('Daily Growth Rate')
    axes[1,2].legend()
    axes[1,2].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('/Users/kapilbhattarai/hydroponic_python/nft_analysis_summary.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    print("Summary plots saved as 'nft_analysis_summary.png'")

def create_comparison_table():
    """Create a comparison table of key metrics"""
    df = pd.read_csv("/Users/kapilbhattarai/hydroponic_python/outputs/LET_EXP001_2024_results.csv")
    
    print("\n" + "="*80)
    print("SUMMARY COMPARISON TABLE: SIMULATED vs COMMERCIAL STANDARDS")
    print("="*80)
    
    comparison_data = [
        ["Metric", "Simulated Value", "Commercial Standard", "Status", "% of Standard"],
        ["-"*20, "-"*15, "-"*18, "-"*8, "-"*12],
        ["Final Biomass (g)", f"{df['Total_Biomass_g'].iloc[-1]:.1f}", "150-300", "FAIL", f"{(df['Total_Biomass_g'].iloc[-1]/200)*100:.1f}%"],
        ["Plant Height (cm)", f"{df['Plant_Height_cm'].iloc[-1]:.1f}", "12-15", "PASS", f"{(df['Plant_Height_cm'].iloc[-1]/13.5)*100:.1f}%"],
        ["Growth Cycle (days)", f"{df['Day'].max()}", "35-45", "FAIL", f"{(df['Day'].max()/40)*100:.1f}%"],
        ["LAI Final", f"{df['LAI'].iloc[-1]:.2f}", "0.8-1.2", "FAIL", f"{(df['LAI'].iloc[-1]/1.0)*100:.1f}%"],
        ["WUE (kg/m³)", f"{df['WUE_kg_m3'].iloc[-1]:.1f}", ">20", "FAIL", f"{(df['WUE_kg_m3'].iloc[-1]/20)*100:.1f}%"],
        ["pH", f"{df['pH'].iloc[-1]:.1f}", "5.5-6.5", "PASS", "100.0%"],
        ["EC (mS/cm)", f"{df['EC'].iloc[-1]:.1f}", "1.5-2.5", "MARGINAL", f"{(df['EC'].iloc[-1]/2.0)*100:.1f}%"],
        ["Temperature (°C)", f"{df['Temp_C'].mean():.1f}", "20-25", "PASS", f"{(df['Temp_C'].mean()/22.5)*100:.1f}%"],
    ]
    
    for row in comparison_data:
        print(f"{row[0]:<20} {row[1]:<15} {row[2]:<18} {row[3]:<8} {row[4]:<12}")
    
    print("\n" + "="*80)

def main():
    create_comparison_table()
    create_summary_plots()

if __name__ == "__main__":
    main()