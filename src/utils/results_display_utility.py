from .core_utils import ParameterError
from typing import Any, Dict, List
from hydro_system_data import DailyResults
from core_utilities import format_scientific, create_summary_table, ParameterAccessError, get_strict_param



class ResultsDisplayUtility:
    """
    Utility for formatting and displaying hydroponic simulation results.

    Provides comprehensive, human-readable reports with clear per-plant vs system-wide categorization.
    All parameters are sourced from configuration, with no hardcoded defaults.
    """
    
    def __init__(self, config: Any):
        """
        Initialize with configuration object.

        Args:
            config: Configuration object with 'display_parameters' and 'phenology_parameters' categories.

        Raises:
            ParameterAccessError: If required configuration categories are missing.
        """
        self.config = config
        # Validate required configuration categories
        for category in ['display_parameters', 'phenology_parameters']:
            if not hasattr(config, category) or not getattr(config, category):
                raise ParameterAccessError(
                    f"Configuration category '{category}' missing or empty. "
                    "Add it to master_parameters.csv."
                )

    def display_detailed_results(self, daily_result: DailyResults) -> str:
        """
        Generate a detailed report for a single day's simulation results.

        Args:
            daily_result: DailyResults object containing simulation data.

        Returns:
            Formatted string report.

        Raises:
            ValueError: If required fields in daily_result are missing.
        """
        output = []
        
        # Validate required fields
        required_fields = [
            'day', 'growth_stage', 'total_biomass', 'daily_growth_rate', 'lai', 'canopy_height_cm',
            'leaf_biomass', 'stem_biomass', 'root_biomass', 'nutrient_concentrations', 'tank_volume',
            'temp_avg', 'rel_humidity', 'vpd', 'integrated_stress_factor', 'accumulated_gdd', 'thermal_time_daily'
        ]
        missing_fields = [f for f in required_fields if getattr(daily_result, f, None) is None]
        if missing_fields:
            raise ValueError(f"Missing required fields in DailyResults: {missing_fields}")

        # Header
        output.append(f"\n{'='*80}")
        output.append(f"🌱 DAY {daily_result.day:2d} - {daily_result.growth_stage:>15} - HYDROPONIC SIMULATION")
        output.append(f"{'='*80}")

        # 1. Quick Summary (Per Plant)
        output.append("\n📊 QUICK SUMMARY:")
        output.append(f"  🎯 Per Plant: {daily_result.total_biomass:.2f} g biomass | "
                      f"{daily_result.daily_growth_rate:.3f} g/day growth | "
                      f"{daily_result.canopy_height_cm:.1f} cm height")
        output.append(f"  🌿 Canopy: LAI {daily_result.lai:.3f} | "
                      f"{daily_result.leaf_number or 'N/A'} leaves | "
                      f"{(daily_result.leaf_area_m2 * 10000) if daily_result.leaf_area_m2 else 'N/A':.1f} cm² leaf area")

        # 2. Per-Plant Biomass Breakdown
        output.append("\n⚖️ PER-PLANT BIOMASS:")
        output.append(f"  {'Component':<15} {'Dry Weight (g)':<15} {'Fresh Weight (g)':<15} {'Growth Rate (g/day)':<20}")
        output.append(f"  {'-'*15} {'-'*15} {'-'*15} {'-'*20}")
        
        biomass_data = [
            ('Total', daily_result.total_biomass, daily_result.shoot_fresh_weight_g, daily_result.daily_growth_rate),
            ('Leaves', daily_result.leaf_biomass, daily_result.leaf_fresh_weight_g, daily_result.leaf_growth_rate),
            ('Stems', daily_result.stem_biomass, daily_result.stem_fresh_weight_g, daily_result.stem_growth_rate),
            ('Roots', daily_result.root_biomass, daily_result.root_fresh_weight_g, daily_result.root_growth_rate)
        ]
        
        for component, dry, fresh, growth in biomass_data:
            fresh_str = f"{fresh:.2f}" if fresh is not None else "N/A"
            growth_str = f"{growth:.3f}" if growth is not None else "N/A"
            output.append(f"  {component:<15} {dry:<15.2f} {fresh_str:<15} {growth_str:<20}")

        # 3. Per-System Totals
        system_config = get_strict_param(self.config, 'system_config', 'system_config')
        plant_count = system_config.n_plants
        system_area = system_config.system_area
        system_biomass = daily_result.total_biomass * plant_count
        system_yield = system_biomass / system_area if system_area > 0 else 0.0
        
        output.append(f"\n🏭 PER-SYSTEM TOTALS ({plant_count} Plants × {system_area} m²):")
        output.append(f"  {'Metric':<25} {'Per Plant':<15} {'Total System':<15} {'Per m²':<15}")
        output.append(f"  {'-'*25} {'-'*15} {'-'*15} {'-'*15}")
        output.append(f"  {'Biomass':<25} {daily_result.total_biomass:<15.2f} g {system_biomass:<15.1f} g {system_yield:<15.1f} g/m²")
        output.append(f"  {'Daily Growth':<25} {daily_result.daily_growth_rate:<15.3f} g/day "
                      f"{(daily_result.daily_growth_rate * plant_count):<15.2f} g/day "
                      f"{(daily_result.daily_growth_rate * plant_count / system_area):<15.2f} g/m²/day")
        output.append(f"  {'Leaf Area':<25} {(daily_result.leaf_area_m2 * 10000) if daily_result.leaf_area_m2 else 'N/A':<15} cm² "
                      f"{(daily_result.leaf_area_m2 * plant_count * 10000) if daily_result.leaf_area_m2 else 'N/A':<15} cm² "
                      f"{daily_result.lai:<15.3f} LAI")

        # 4. Carbon Balance (Per Plant)
        output.append("\n🔄 CARBON BALANCE (Per Plant):")
        carbon_data = {
            'Photosynthesis': daily_result.photosynthesis_rate,
            'Maintenance Resp.': daily_result.maintenance_respiration,
            'Growth Resp.': daily_result.growth_respiration,
            'Total Respiration': daily_result.respiration_rate,
            'NET ASSIMILATION': daily_result.net_assimilation
        }
        
        if all(v is not None for v in carbon_data.values()):
            output.append(f"  {'Process':<20} {'Rate (g/day)':<15} {'Balance':<15}")
            output.append(f"  {'-'*20} {'-'*15} {'-'*15}")
            for process, rate in carbon_data.items():
                balance = '→' if process == 'Photosynthesis' else '←' if 'Resp.' in process else '='
                output.append(f"  {process:<20} {rate:<15.4f} {balance:<15}")
        else:
            output.append("  Carbon balance data incomplete")

        # 5. Nutrient Status (System-wide)
        output.append("\n💧 NUTRIENT SOLUTION STATUS (System-wide):")
        output.append(f"  {'Nutrient':<10} {'Concentration':<15} {'Uptake (mg/day)':<20} {'Status':<15}")
        output.append(f"  {'-'*10} {'-'*15} {'-'*20} {'-'*15}")
        
        nutrients = [
            ('N-NO₃', 'N-NO3', daily_result.nutrient_concentrations.get('N-NO3'), daily_result.nitrogen_uptake_mg),
            ('P-PO₄', 'P-PO4', daily_result.nutrient_concentrations.get('P-PO4'), daily_result.phosphorus_uptake_mg),
            ('K', 'K', daily_result.nutrient_concentrations.get('K'), daily_result.potassium_uptake_mg),
            ('Ca', 'Ca', daily_result.nutrient_concentrations.get('Ca'), None),
            ('Mg', 'Mg', daily_result.nutrient_concentrations.get('Mg'), None)
        ]
        
        nutrient_thresholds = get_strict_param(self.config, 'display_parameters', 'nutrient_thresholds')
        for name, key, conc, uptake in nutrients:
            if conc is not None:
                if key not in nutrient_thresholds:
                    raise ParameterError(f"Nutrient thresholds for '{key}' missing from configuration")
                optimal = get_strict_param(nutrient_thresholds[key], 'optimal')
                low = get_strict_param(nutrient_thresholds[key], 'low')
                status = "🟢 Optimal" if conc > optimal else "🟡 Low" if conc > low else "🔴 Critical"
                uptake_str = f"{uptake:.2f}" if uptake is not None else "N/A"
                output.append(f"  {name:<10} {conc:<15.1f} mg/L {uptake_str:<20} {status:<15}")
            else:
                output.append(f"  {name:<10} {'N/A':<15} {'N/A':<20} {'Data Missing':<15}")
        
        # System Parameters
        system_params = [
            ('EC', daily_result.ec, 'ec_thresholds', lambda x: "🟢 Optimal" if x > 1.0 else "🔴 Low"),
            ('pH', daily_result.solution_ph, 'ph_thresholds', lambda x: "🟢 Optimal" if 5.5 <= x <= 6.5 else "🟡 Off-target"),
            ('Volume', daily_result.tank_volume, None, lambda x: "🟢 Adequate")
        ]
        
        for name, value, threshold_key, status_func in system_params:
            if value is not None:
                if threshold_key:
                    thresholds = get_strict_param(self.config, 'display_parameters', threshold_key)
                    status = status_func(value)
                else:
                    status = status_func(value)
                output.append(f"  {name:<10} {value:<15.2f} {'':<20} {status:<15}")
            else:
                output.append(f"  {name:<10} {'N/A':<15} {'':<20} {'Data Missing':<15}")

        # 6. Environmental Conditions (System-wide)
        output.append("\n🌡️ ENVIRONMENTAL CONDITIONS (System-wide):")
        output.append(f"  {'Parameter':<20} {'Value':<15} {'Target':<15} {'Status':<15}")
        output.append(f"  {'-'*20} {'-'*15} {'-'*15} {'-'*15}")
        
        env_thresholds = get_strict_param(self.config, 'display_parameters', 'environmental_thresholds')
        env_data = [
            ('Temperature', daily_result.temp_avg, env_thresholds['temperature'], '20-28°C',
             lambda x: "🟢 Optimal" if x['min'] <= x['value'] <= x['max'] else "🟡 Warm" if x['value'] > x['max'] else "🟡 Cool"),
            ('Humidity', daily_result.rel_humidity, env_thresholds['humidity'], '50-80%',
             lambda x: "🟢 Optimal" if x['min'] <= x['value'] <= x['max'] else "🟡 Low" if x['value'] < x['min'] else "🟡 High"),
            ('CO₂', daily_result.co2_concentration, env_thresholds['co2'], '≥400 ppm',
             lambda x: "🟢 Optimal" if x['value'] >= x['min'] else "🟡 Low"),
            ('VPD', daily_result.vpd, env_thresholds['vpd'], '0.6-1.2 kPa',
             lambda x: "🟢 Optimal" if x['min'] <= x['value'] <= x['max'] else "🟡 High" if x['value'] > x['max'] else "🟡 Low")
        ]
        
        for name, value, thresholds, target, status_func in env_data:
            if value is not None:
                max_val = thresholds.get('max')
                if max_val is None:
                    max_val = float('inf')
                status = status_func({'value': value, 'min': thresholds['min'], 'max': max_val})
                output.append(f"  {name:<20} {value:<15.1f} {target:<15} {status:<15}")
            else:
                output.append(f"  {name:<20} {'N/A':<15} {target:<15} {'Data Missing':<15}")

        # 7. Stress Factors (Per Plant)
        output.append("\n😰 STRESS FACTORS (Per Plant):")
        output.append(f"  {'Stress Type':<20} {'Level':<15} {'Effect':<15} {'Status':<15}")
        output.append(f"  {'-'*20} {'-'*15} {'-'*15} {'-'*15}")
        
        stress_thresholds = get_strict_param(self.config, 'display_parameters', 'stress_thresholds')
        stresses = [
            ('Temperature', daily_result.temperature_stress_level, daily_result.temperature_stress_factor),
            ('Water', daily_result.water_stress, daily_result.water_stress),
            ('Nutrient', daily_result.nutrient_stress, daily_result.nutrient_stress),
            ('Nitrogen', daily_result.nitrogen_stress_factor, daily_result.nitrogen_stress_factor),
            ('Salinity', daily_result.salinity_stress, daily_result.salinity_stress)
        ]
        
        for name, level, effect in stresses:
            if level is not None and effect is not None:
                status = ("🟢 None" if level < stress_thresholds['none'] else
                          "🟡 Mild" if level < stress_thresholds['mild'] else
                          "🟠 Moderate" if level < stress_thresholds['moderate'] else
                          "🔴 Severe")
                output.append(f"  {name:<20} {level:<15.3f} {effect:<15.3f} {status:<15}")
            else:
                output.append(f"  {name:<20} {'N/A':<15} {'N/A':<15} {'Data Missing':<15}")

        # 8. Development Progress (Per Plant)
        output.append("\n📅 DEVELOPMENT PROGRESS (Per Plant):")
        harvest_gdd = get_strict_param(self.config, 'phenology_parameters', 'harvest_gdd')
        progress = min(100.0, (daily_result.accumulated_gdd / harvest_gdd) * 100) if harvest_gdd > 0 else 0.0
        
        output.append(f"  • Accumulated GDD: {daily_result.accumulated_gdd:.1f}°C-days (Target: {harvest_gdd:.0f}°C-days)")
        output.append(f"  • Daily Thermal Time: {daily_result.thermal_time_daily:.1f}°C-days")
        output.append(f"  • Development Rate: {daily_result.development_rate or 'N/A':.4f}")
        output.append(f"  • Progress to Harvest: {progress:.1f}%")

        # 9. Efficiency Metrics (System-wide)
        output.append("\n📊 EFFICIENCY METRICS (System-wide):")
        output.append(f"  • Water Use Efficiency: {daily_result.water_use_efficiency or 'N/A':.2f} L/kg")
        output.append(f"  • Light Use Efficiency: {daily_result.light_interception or 'N/A':.3f} g/MJ")
        if daily_result.daily_growth_rate and daily_result.nitrogen_uptake_mg:
            n_efficiency = (daily_result.daily_growth_rate / daily_result.nitrogen_uptake_mg) * 1000
            output.append(f"  • Nitrogen Use Efficiency: {n_efficiency:.1f} g biomass/g N")
        else:
            output.append("  • Nitrogen Use Efficiency: Data not available")
        output.append(f"  • System Yield: {system_yield:.1f} g/m²")

        # 10. Projections
        if daily_result.day > 1 and daily_result.daily_growth_rate and daily_result.thermal_time_daily:
            remaining_gdd = max(0, harvest_gdd - daily_result.accumulated_gdd)
            days_to_harvest = remaining_gdd / daily_result.thermal_time_daily if daily_result.thermal_time_daily > 0 else 0
            projected_yield = daily_result.total_biomass + (daily_result.daily_growth_rate * days_to_harvest)
            projected_system_yield = projected_yield * plant_count / system_area if system_area > 0 else 0.0
            
            output.append("\n🔮 PROJECTIONS (Based on Current Performance):")
            output.append(f"  • Days to Harvest: {days_to_harvest:.1f} days")
            output.append(f"  • Projected Final Biomass: {projected_yield:.1f} g/plant")
            output.append(f"  • Projected System Yield: {projected_system_yield:.1f} g/m²")

        # Footer
        output.append(f"\n{'-'*80}")
        output.append(f"📋 Note: Biomass values are PER PLANT. Multiply by {plant_count} for total system values.")
        output.append("📋 Note: Environmental values are SYSTEM-WIDE (affect all plants).")
        output.append(f"{'='*80}")
        
        return "\n".join(output)

def create_results_display_utility(config: Any) -> ResultsDisplayUtility:
    """
    Create a results display utility instance.

    Args:
        config: Configuration object with required parameters.

    Returns:
        Configured ResultsDisplayUtility instance.

    Raises:
        ParameterAccessError: If configuration is invalid.
    """
    return ResultsDisplayUtility(config)
