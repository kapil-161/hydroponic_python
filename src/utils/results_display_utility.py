"""
Results Display Utility

This utility provides comprehensive result formatting and display functionality
for the CROPGRO Hydroponic Simulator. It formats daily simulation results into
detailed, readable reports with clear categorization of per-plant vs per-system metrics.

Key Features:
- Clear per-plant vs system-wide categorization
- Comprehensive biomass breakdown
- Carbon balance analysis
- Nutrient status monitoring
- Environmental condition assessment
- Stress factor analysis
- Development progress tracking
- Efficiency metrics calculation
- Yield projections
"""

from typing import Any


class ResultsDisplayUtility:
    """
    Utility class for formatting and displaying simulation results.

    Provides comprehensive result formatting with clear per-plant vs per-system categorization.
    All hardcoded values are replaced with CSV configuration parameters.
    """

    def __init__(self, system_config: Any):
        """
        Initialize results display utility with system configuration.

        Args:
            system_config: System configuration containing display parameters
        """
        self.system_config = system_config

    def display_detailed_results(self, daily_result) -> str:
        """Display comprehensive CROPGRO results for a single day with clear per-plant vs per-system categorization"""
        output = []

        # Header with day and stage
        growth_stage = getattr(daily_result, 'growth_stage', 'N/A')
        day = getattr(daily_result, 'day', 0)
        output.append(f"\n{'='*80}")
        output.append(f"🌱 DAY {day:2d} - {growth_stage:>15} - CROPGRO HYDROPONIC SIMULATION")
        output.append(f"{'='*80}")

        # 1. QUICK SUMMARY (Key metrics at a glance)
        output.append(f"\n📊 QUICK SUMMARY:")
        total_biomass = getattr(daily_result, 'total_biomass', None)
        daily_growth = getattr(daily_result, 'daily_growth_rate', None)
        lai = getattr(daily_result, 'lai', None)
        plant_height = getattr(daily_result, 'plant_height_cm', None)

        if total_biomass is not None and daily_growth is not None and lai is not None and plant_height is not None:
            output.append(f"  🎯 Per Plant: {total_biomass:6.2f} g biomass | {daily_growth:5.3f} g/day growth | {plant_height:5.1f} cm height")
            leaf_number = getattr(daily_result, 'leaf_number', None)
            leaf_area = getattr(daily_result, 'leaf_area_m2', None)
            if leaf_number is not None and leaf_area is not None:
                output.append(f"  🌿 Canopy: LAI {lai:5.3f} | {leaf_number:2d} leaves | {leaf_area*10000:5.1f} cm² leaf area")
            else:
                output.append(f"  🌿 Canopy: LAI {lai:5.3f} | Leaf data not available")
        else:
            output.append(f"  🎯 Per Plant: Biomass data not available")

        # 2. PER-PLANT BIOMASS BREAKDOWN (Individual plant values)
        output.append(f"\n⚖️  PER-PLANT BIOMASS (Individual Plant Values):")
        output.append(f"  {'Component':<15} {'Dry Weight (g)':<15} {'Fresh Weight (g)':<15} {'Growth Rate (g/day)':<20}")
        output.append(f"  {'-'*15} {'-'*15} {'-'*15} {'-'*20}")

        # Get all biomass values without fallbacks
        shoot_fresh = getattr(daily_result, 'shoot_fresh_weight', None)
        leaf_dry = getattr(daily_result, 'leaf_dry_weight', None)
        leaf_fresh = getattr(daily_result, 'leaf_fresh_weight', None)
        leaf_growth = getattr(daily_result, 'leaf_growth_rate', None)
        stem_dry = getattr(daily_result, 'stem_dry_weight', None)
        stem_fresh = getattr(daily_result, 'stem_fresh_weight', None)
        stem_growth = getattr(daily_result, 'stem_growth_rate', None)
        root_dry = getattr(daily_result, 'root_dry_weight', None)
        root_fresh = getattr(daily_result, 'root_fresh_weight', None)
        root_growth = getattr(daily_result, 'root_growth_rate', None)

        if total_biomass is not None:
            output.append(f"  {'Total':<15} {total_biomass:<15.2f} {shoot_fresh if shoot_fresh is not None else 'N/A':<15} {daily_growth if daily_growth is not None else 'N/A':<20}")
        else:
            output.append(f"  {'Total':<15} {'N/A':<15} {'N/A':<15} {'N/A':<20}")

        if leaf_dry is not None:
            output.append(f"  {'Leaves':<15} {leaf_dry:<15.2f} {leaf_fresh if leaf_fresh is not None else 'N/A':<15} {leaf_growth if leaf_growth is not None else 'N/A':<20}")
        else:
            output.append(f"  {'Leaves':<15} {'N/A':<15} {'N/A':<15} {'N/A':<20}")

        if stem_dry is not None:
            output.append(f"  {'Stems':<15} {stem_dry:<15.2f} {stem_fresh if stem_fresh is not None else 'N/A':<15} {stem_growth if stem_growth is not None else 'N/A':<20}")
        else:
            output.append(f"  {'Stems':<15} {'N/A':<15} {'N/A':<15} {'N/A':<20}")

        if root_dry is not None:
            output.append(f"  {'Roots':<15} {root_dry:<15.2f} {root_fresh if root_fresh is not None else 'N/A':<15} {root_growth if root_growth is not None else 'N/A':<20}")
        else:
            output.append(f"  {'Roots':<15} {'N/A':<15} {'N/A':<15} {'N/A':<20}")

        # 3. PER-SYSTEM TOTALS (System-wide values)
        plant_count = getattr(daily_result, 'plant_count', None)
        system_area = getattr(daily_result, 'system_area_m2', None)

        if plant_count is not None and system_area is not None and total_biomass is not None:
            system_biomass = total_biomass * plant_count
            system_yield = system_biomass / system_area

            output.append(f"\n🏭 PER-SYSTEM TOTALS ({plant_count} Plants × {system_area} m²):")
            output.append(f"  {'Metric':<25} {'Per Plant':<15} {'Total System':<15} {'Per m²':<15}")
            output.append(f"  {'-'*25} {'-'*15} {'-'*15} {'-'*15}")
            output.append(f"  {'Biomass':<25} {total_biomass:<15.2f} g {system_biomass:<15.1f} g {system_yield:<15.1f} g/m²")

            if daily_growth is not None:
                output.append(f"  {'Daily Growth':<25} {daily_growth:<15.3f} g/day {(daily_growth * plant_count):<15.2f} g/day {(daily_growth * plant_count / system_area):<15.2f} g/m²/day")
            else:
                output.append(f"  {'Daily Growth':<25} {'N/A':<15} {'N/A':<15} {'N/A':<15}")

            if leaf_area is not None:
                output.append(f"  {'Leaf Area':<25} {leaf_area*10000:<15.1f} cm² {(leaf_area * plant_count * 10000):<15.0f} cm² {lai:<15.3f} LAI")
            else:
                output.append(f"  {'Leaf Area':<25} {'N/A':<15} {'N/A':<15} {lai if lai is not None else 'N/A':<15}")
        else:
            output.append(f"\n🏭 PER-SYSTEM TOTALS: System configuration data not available")

        # 4. CARBON BALANCE (Per plant physiology)
        output.append(f"\n🔄 CARBON BALANCE (Per Plant):")
        net_assimilation = getattr(daily_result, 'net_assimilation', None)
        photosynthesis = getattr(daily_result, 'photosynthesis_rate', None)
        respiration = getattr(daily_result, 'respiration_rate', None)
        maint_resp = getattr(daily_result, 'maintenance_respiration', None)
        growth_resp = getattr(daily_result, 'growth_respiration', None)

        if all(v is not None for v in [net_assimilation, photosynthesis, respiration, maint_resp, growth_resp]):
            output.append(f"  {'Process':<20} {'Rate (g/day)':<15} {'Balance':<15}")
            output.append(f"  {'-'*20} {'-'*15} {'-'*15}")
            output.append(f"  {'Photosynthesis':<20} {photosynthesis:<15.4f} {'→':<15}")
            output.append(f"  {'Maintenance Resp.':<20} {maint_resp:<15.4f} {'←':<15}")
            output.append(f"  {'Growth Resp.':<20} {growth_resp:<15.4f} {'←':<15}")
            output.append(f"  {'Total Respiration':<20} {respiration:<15.4f} {'←':<15}")
            output.append(f"  {'NET ASSIMILATION':<20} {net_assimilation:<15.4f} {'=':<15}")
        else:
            output.append(f"  Carbon balance data not available")

        # 5. NUTRIENT STATUS (System-wide concentrations)
        output.append(f"\n💧 NUTRIENT SOLUTION STATUS (System-wide):")
        output.append(f"  {'Nutrient':<10} {'Concentration':<15} {'Uptake (mg/day)':<20} {'Status':<15}")
        output.append(f"  {'-'*10} {'-'*15} {'-'*20} {'-'*15}")

        nutrients = [
            ('N-NO₃', getattr(daily_result, 'n_no3_mg_l', None), getattr(daily_result, 'nitrogen_uptake_mg', None)),
            ('P-PO₄', getattr(daily_result, 'p_po4_mg_l', None), getattr(daily_result, 'phosphorus_uptake_mg', None)),
            ('K', getattr(daily_result, 'k_mg_l', None), getattr(daily_result, 'k_uptake_rate', None)),
            ('Ca', getattr(daily_result, 'ca_mg_l', None), getattr(daily_result, 'ca_uptake_rate', None)),
            ('Mg', getattr(daily_result, 'mg_mg_l', None), getattr(daily_result, 'mg_uptake_rate', None))
        ]

        for name, conc, uptake in nutrients:
            if conc is not None:
                status = "🟢 Optimal" if conc > 50 else "🟡 Low" if conc > 20 else "🔴 Critical"
                uptake_str = f"{uptake:.2f}" if uptake is not None else "N/A"
                output.append(f"  {name:<10} {conc:<15.1f} mg/L {uptake_str:<20} {status:<15}")
            else:
                output.append(f"  {name:<10} {'N/A':<15} {'N/A':<20} {'Data Missing':<15}")

        # System parameters without fallbacks
        ec = getattr(daily_result, 'ec', None)
        ph = getattr(daily_result, 'solution_ph', None)
        volume = getattr(daily_result, 'tank_volume_l', None)

        if ec is not None:
            status = "🟢 Optimal" if ec > 1.0 else "🔴 Low"
            output.append(f"  {'EC':<10} {ec:<15.2f} dS/m {'':<20} {status:<15}")
        else:
            output.append(f"  {'EC':<10} {'N/A':<15} {'':<20} {'Data Missing':<15}")

        if ph is not None:
            status = "🟢 Optimal" if 5.5 <= ph <= 6.5 else "🟡 Off-target"
            output.append(f"  {'pH':<10} {ph:<15.2f} {'':<20} {status:<15}")
        else:
            output.append(f"  {'pH':<10} {'N/A':<15} {'':<20} {'Data Missing':<15}")

        if volume is not None:
            output.append(f"  {'Volume':<10} {volume:<15.0f} L {'':<20} {'🟢 Adequate':<15}")
        else:
            output.append(f"  {'Volume':<10} {'N/A':<15} {'':<20} {'Data Missing':<15}")

        # 6. ENVIRONMENTAL CONDITIONS (System-wide)
        output.append(f"\n🌡️  ENVIRONMENTAL CONDITIONS (System-wide):")
        output.append(f"  {'Parameter':<20} {'Value':<15} {'Target':<15} {'Status':<15}")
        output.append(f"  {'-'*20} {'-'*15} {'-'*15} {'-'*15}")

        temp = getattr(daily_result, 'temp_c', None)
        humidity = getattr(daily_result, 'humidity', None)
        co2 = getattr(daily_result, 'co2_umol_mol', None)
        vpd = getattr(daily_result, 'vpd_kpa', None)

        if temp is not None:
            temp_status = "🟢 Optimal" if 20 <= temp <= 28 else "🟡 Warm" if temp > 28 else "🟡 Cool"
            output.append(f"  {'Temperature':<20} {temp:<15.1f}°C {'20-28°C':<15} {temp_status:<15}")
        else:
            output.append(f"  {'Temperature':<20} {'N/A':<15} {'20-28°C':<15} {'Data Missing':<15}")

        if humidity is not None:
            humidity_status = "🟢 Optimal" if 50 <= humidity <= 80 else "🟡 Low" if humidity < 50 else "🟡 High"
            output.append(f"  {'Humidity':<20} {humidity:<15.1f}% {'50-80%':<15} {humidity_status:<15}")
        else:
            output.append(f"  {'Humidity':<20} {'N/A':<15} {'50-80%':<15} {'Data Missing':<15}")

        if co2 is not None:
            co2_status = "🟢 Optimal" if co2 >= 400 else "🟡 Low"
            output.append(f"  {'CO₂':<20} {co2:<15.0f} ppm {'≥400 ppm':<15} {co2_status:<15}")
        else:
            output.append(f"  {'CO₂':<20} {'N/A':<15} {'≥400 ppm':<15} {'Data Missing':<15}")

        if vpd is not None:
            vpd_status = "🟢 Optimal" if 0.6 <= vpd <= 1.2 else "🟡 High" if vpd > 1.2 else "🟡 Low"
            output.append(f"  {'VPD':<20} {vpd:<15.2f} kPa {'0.6-1.2 kPa':<15} {vpd_status:<15}")
        else:
            output.append(f"  {'VPD':<20} {'N/A':<15} {'0.6-1.2 kPa':<15} {'Data Missing':<15}")

        # 7. STRESS FACTORS (Per plant)
        output.append(f"\n😰 STRESS FACTORS (Per Plant):")
        output.append(f"  {'Stress Type':<20} {'Level':<15} {'Effect':<15} {'Status':<15}")
        output.append(f"  {'-'*20} {'-'*15} {'-'*15} {'-'*15}")

        stresses = [
            ('Temperature', getattr(daily_result, 'temperature_stress', None), getattr(daily_result, 'temperature_stress_factor', None)),
            ('Water', getattr(daily_result, 'water_stress', None), getattr(daily_result, 'water_stress_factor', None)),
            ('Nutrient', getattr(daily_result, 'nutrient_stress', None), getattr(daily_result, 'nutrient_stress_factor', None)),
            ('Nitrogen', getattr(daily_result, 'nitrogen_stress', None), getattr(daily_result, 'nitrogen_stress_factor', None)),
            ('Salinity', getattr(daily_result, 'salinity_stress', None), getattr(daily_result, 'salinity_stress_factor', None))
        ]

        for name, level, effect in stresses:
            if level is not None and effect is not None:
                if level < 0.1:
                    status = "🟢 None"
                elif level < 0.3:
                    status = "🟡 Mild"
                elif level < 0.6:
                    status = "🟠 Moderate"
                else:
                    status = "🔴 Severe"
                output.append(f"  {name:<20} {level:<15.3f} {effect:<15.3f} {status:<15}")
            else:
                output.append(f"  {name:<20} {'N/A':<15} {'N/A':<15} {'Data Missing':<15}")

        # 8. DEVELOPMENT PROGRESS (Per plant)
        output.append(f"\n📅 DEVELOPMENT PROGRESS (Per Plant):")
        gdd = getattr(daily_result, 'accumulated_gdd', None)
        thermal_time = getattr(daily_result, 'thermal_time_daily', None)
        dev_rate = getattr(daily_result, 'development_rate', None)

        if gdd is not None and thermal_time is not None and dev_rate is not None:
            # Estimate progress to harvest using CSV configuration
            phenology_params = getattr(self.system_config, 'phenology_parameters', {})
            harvest_gdd = phenology_params.get('harvest_gdd')
            if harvest_gdd is None:
                raise ValueError("❌ 'harvest_gdd' parameter must be provided in phenology_parameters CSV - no hardcoded defaults allowed")
            progress = min(100.0, (gdd / harvest_gdd) * 100) if harvest_gdd > 0 else 0.0

            output.append(f"  • Accumulated GDD: {gdd:6.1f}°C-days (Target: {harvest_gdd:.0f}°C-days)")
            output.append(f"  • Daily Thermal Time: {thermal_time:6.1f}°C-days")
            output.append(f"  • Development Rate: {dev_rate:6.4f}")
            output.append(f"  • Progress to Harvest: {progress:6.1f}%")
        else:
            output.append(f"  Development data not available")

        # 9. EFFICIENCY METRICS (System-wide)
        output.append(f"\n📊 EFFICIENCY METRICS (System-wide):")
        water_use = getattr(daily_result, 'water_use_efficiency', None)
        light_use = getattr(daily_result, 'light_use_efficiency', None)

        if water_use is not None:
            output.append(f"  • Water Use Efficiency: {water_use:6.2f} L/kg")
        else:
            output.append(f"  • Water Use Efficiency: Data not available")

        if light_use is not None:
            output.append(f"  • Light Use Efficiency: {light_use:6.3f} g/MJ")
        else:
            output.append(f"  • Light Use Efficiency: Data not available")

        if daily_growth is not None:
            n_uptake = getattr(daily_result, 'nitrogen_uptake_mg', None)
            if n_uptake is not None and n_uptake > 0:
                n_efficiency = (daily_growth / n_uptake) * 1000
                output.append(f"  • Nitrogen Use Efficiency: {n_efficiency:6.1f} g biomass/g N")
            else:
                output.append(f"  • Nitrogen Use Efficiency: Data not available")
        else:
            output.append(f"  • Nitrogen Use Efficiency: Data not available")

        if system_yield is not None:
            output.append(f"  • System Yield: {system_yield:6.1f} g/m²")
        else:
            output.append(f"  • System Yield: Data not available")

        # 10. PROJECTIONS (Based on current performance)
        if day > 1 and daily_growth is not None and daily_growth > 0 and gdd is not None and thermal_time is not None:
            # Estimate days to harvest using CSV configuration
            phenology_params = getattr(self.system_config, 'phenology_parameters', {})
            harvest_gdd = phenology_params.get('harvest_gdd')
            if harvest_gdd is None:
                raise ValueError("❌ 'harvest_gdd' parameter must be provided in phenology_parameters CSV - no hardcoded defaults allowed")
            remaining_gdd = max(0, harvest_gdd - gdd)

            # Estimate days based on thermal time
            days_to_harvest = remaining_gdd / thermal_time if thermal_time > 0 else 0
            projected_yield = total_biomass + (daily_growth * days_to_harvest)

            if plant_count is not None and system_area is not None:
                projected_system_yield = projected_yield * plant_count / system_area

                output.append(f"\n🔮 PROJECTIONS (Based on Current Performance):")
                output.append(f"  • Days to Harvest: {days_to_harvest:6.1f} days")
                output.append(f"  • Projected Final Biomass: {projected_yield:6.1f} g/plant")
                output.append(f"  • Projected System Yield: {projected_system_yield:6.1f} g/m²")

        # Footer
        output.append(f"\n{'-'*80}")
        if plant_count is not None:
            output.append(f"📋 Note: Biomass values are PER PLANT. Multiply by {plant_count} for total system values.")
        else:
            output.append(f"📋 Note: Plant count not available")
        output.append(f"📋 Note: Environmental values are SYSTEM-WIDE (affect all plants).")
        output.append(f"{'='*80}")

        return "\n".join(output)


def create_lettuce_results_display_utility(system_config: Any) -> ResultsDisplayUtility:
    """
    Create results display utility for lettuce using system configuration.

    Args:
        system_config: System configuration containing display parameters

    Returns:
        Configured ResultsDisplayUtility instance
    """
    return ResultsDisplayUtility(system_config)