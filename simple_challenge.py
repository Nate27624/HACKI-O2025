#!/usr/bin/env python3

import pandas as pd
import numpy as np
import sys
import warnings
warnings.filterwarnings('ignore')

sys.path.append('ieee738')
from ieee738.ieee738 import ConductorParams
import ieee738.ieee738 as ieee738

def load_data():
    """Load grid data"""
    lines_df = pd.read_csv('hawaii40_osu/csv/lines.csv')
    flows_df = pd.read_csv('hawaii40_osu/line_flows_nominal.csv')
    conductor_df = pd.read_csv('ieee738/conductor_library.csv')
    buses_df = pd.read_csv('hawaii40_osu/csv/buses.csv')
    
    grid_data = lines_df.merge(flows_df, on='name')
    grid_data = grid_data.merge(conductor_df, left_on='conductor', right_on='ConductorName')
    grid_data = grid_data.merge(buses_df[['name', 'v_nom']], left_on='bus0', right_on='name', suffixes=('', '_bus'))
    
    return grid_data, conductor_df

def calculate_rating(conductor_name, mot, temp, wind, conductor_df):
    """Calculate IEEE 738 rating"""
    conductor_row = conductor_df[conductor_df['ConductorName'] == conductor_name].iloc[0]
    
    params = {
        'Ta': temp, 'WindVelocity': wind, 'TLo': 25, 'THi': 50,
        'RLo': conductor_row['RES_25C'] / 5280, 'RHi': conductor_row['RES_50C'] / 5280,
        'Diameter': conductor_row['CDRAD_in'] * 2, 'Tc': mot,
        'WindAngleDeg': 90, 'SunTime': 12, 'Date': '12 Jun',
        'Emissivity': 0.8, 'Absorptivity': 0.8, 'Direction': 'EastWest',
        'Atmosphere': 'Clear', 'Elevation': 1000, 'Latitude': 27
    }
    
    try:
        cp = ConductorParams(**params)
        conductor = ieee738.Conductor(cp)
        return conductor.steady_state_thermal_rating()
    except:
        return None

def find_critical_temperature(grid_data, conductor_df):
    """STEP 1: Find when lines first overload"""
    for temp in range(25, 70):
        for _, line in grid_data.iterrows():
            rating_amps = calculate_rating(line['conductor'], line['MOT'], temp, 2.0, conductor_df)
            if rating_amps:
                rating_mva = np.sqrt(3) * rating_amps * line['v_nom'] * 1000 / 1e6
                loading = (line['p0_nominal'] / rating_mva) * 100
                if loading > 100:
                    return temp, line['branch_name'], loading
    return None, None, None

def identify_critical_lines(grid_data, conductor_df, temp=50):
    """STEP 2: Find most vulnerable lines"""
    results = []
    for _, line in grid_data.iterrows():
        rating_amps = calculate_rating(line['conductor'], line['MOT'], temp, 2.0, conductor_df)
        if rating_amps:
            rating_mva = np.sqrt(3) * rating_amps * line['v_nom'] * 1000 / 1e6
            loading = (line['p0_nominal'] / rating_mva) * 100
            results.append((line['branch_name'], line['conductor'], loading))
    
    return sorted(results, key=lambda x: x[2], reverse=True)

def assess_system_stress(grid_data, conductor_df, temp):
    """STEP 3: Categorize system stress"""
    loadings = []
    for _, line in grid_data.iterrows():
        rating_amps = calculate_rating(line['conductor'], line['MOT'], temp, 2.0, conductor_df)
        if rating_amps:
            rating_mva = np.sqrt(3) * rating_amps * line['v_nom'] * 1000 / 1e6
            loading = (line['p0_nominal'] / rating_mva) * 100
            loadings.append(loading)
    
    loadings = np.array(loadings)
    critical = len(loadings[loadings >= 90])
    caution = len(loadings[(loadings >= 60) & (loadings < 90)])
    normal = len(loadings[loadings < 60])
    
    return critical, caution, normal, loadings.max()

def main():
    """Execute challenge"""
    grid_data, conductor_df = load_data()
    
    # CHALLENGE 1: Critical Temperature
    temp, line, loading = find_critical_temperature(grid_data, conductor_df)
    print(f"CHALLENGE 1: First overload at {temp}°C")
    print(f"  Line: {line}")
    print(f"  Loading: {loading:.1f}%")
    
    # CHALLENGE 2: Critical Lines
    critical_lines = identify_critical_lines(grid_data, conductor_df, 50)
    print(f"\nCHALLENGE 2: Most critical lines at 50°C:")
    for i, (name, conductor, loading) in enumerate(critical_lines[:5]):
        print(f"  {i+1}. {name[:50]}")
        print(f"     Conductor: {conductor}, Loading: {loading:.1f}%")
    
    # CHALLENGE 3: System Stress
    print(f"\nCHALLENGE 3: System stress levels:")
    for temp in [30, 40, 50, 60]:
        critical, caution, normal, max_load = assess_system_stress(grid_data, conductor_df, temp)
        if critical > 0:
            status = "CRITICAL"
        elif caution > 5:
            status = "CAUTION"  
        else:
            status = "NORMAL"
        print(f"  {temp}°C: {critical} critical, {caution} caution, {normal} normal - {status}")
        print(f"         Max loading: {max_load:.1f}%")

if __name__ == "__main__":
    main()