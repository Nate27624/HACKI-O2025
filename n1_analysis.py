#!/usr/bin/env python3

import pypsa
import pandas as pd
import numpy as np
import sys
import warnings
warnings.filterwarnings('ignore')

sys.path.append('ieee738')
from ieee738.ieee738 import ConductorParams
import ieee738.ieee738 as ieee738

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

def run_n1_analysis():
    """N-1 Contingency Analysis"""
    # Load data
    network = pypsa.Network()
    network.import_from_csv_folder('hawaii40_osu/csv')
    network.pf()
    
    lines_df = pd.read_csv('hawaii40_osu/csv/lines.csv')
    conductor_df = pd.read_csv('ieee738/conductor_library.csv')
    buses_df = pd.read_csv('hawaii40_osu/csv/buses.csv')
    
    # Merge for conductor info
    line_info = lines_df.merge(conductor_df, left_on='conductor', right_on='ConductorName')
    line_info = line_info.merge(buses_df[['name', 'v_nom']], left_on='bus0', right_on='name', suffixes=('', '_bus'))
    
    violations = []
    
    # Test key contingencies
    test_lines = ['L0', 'L1', 'L17', 'L18']  # Sample critical lines
    
    for line_out in test_lines:
        cont_network = network.copy()
        cont_network.lines.drop(line_out, inplace=True)
        
        try:
            cont_network.pf()
            flows = cont_network.lines_t.p0.iloc[0]
            
            line_violations = []
            for line_name, flow in flows.items():
                if line_name in line_info['name'].values:
                    line_data = line_info[line_info['name'] == line_name].iloc[0]
                    rating_amps = calculate_rating(line_data['conductor'], line_data['MOT'], 35, 2.0, conductor_df)
                    
                    if rating_amps:
                        rating_mva = np.sqrt(3) * rating_amps * line_data['v_nom'] * 1000 / 1e6
                        loading = (abs(flow) / rating_mva) * 100
                        
                        if loading > 80:
                            line_violations.append((line_name, loading))
            
            if line_violations:
                violations.append((line_out, line_violations))
                
        except:
            continue
    
    return violations

def format_n1_output(violations):
    """Format N-1 results like the example"""
    for contingency, line_violations in violations:
        # Get readable name
        lines_df = pd.read_csv('hawaii40_osu/csv/lines.csv')
        cont_name = lines_df[lines_df['name'] == contingency]['branch_name'].iloc[0]
        
        print(f'For loss of "{cont_name}"')
        print("Ratings Issues:")
        
        for line_name, loading in line_violations:
            line_readable = lines_df[lines_df['name'] == line_name]['branch_name'].iloc[0]
            print(f'"{line_readable}" {loading:.0f}%')
        print()

def main():
    """Execute N-1 analysis"""
    print("N-1 CONTINGENCY ANALYSIS")
    print("=" * 40)
    
    violations = run_n1_analysis()
    
    if violations:
        format_n1_output(violations)
    else:
        print("No violations found in tested contingencies")

if __name__ == "__main__":
    main()