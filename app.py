#!/usr/bin/env python3

from flask import Flask, render_template, request, jsonify
import pandas as pd
import numpy as np
import json
import sys
import warnings
warnings.filterwarnings('ignore')

sys.path.append('ieee738')
from ieee738.ieee738 import ConductorParams
import ieee738.ieee738 as ieee738

app = Flask(__name__)

class GridAnalyzer:
    def __init__(self):
        self.load_data()
        
    def load_data(self):
        """Load all grid data"""
        self.lines_df = pd.read_csv('hawaii40_osu/csv/lines.csv')
        self.flows_df = pd.read_csv('hawaii40_osu/line_flows_nominal.csv')
        self.conductor_df = pd.read_csv('ieee738/conductor_library.csv')
        self.buses_df = pd.read_csv('hawaii40_osu/csv/buses.csv')
        
        # Merge data
        self.grid_data = self.lines_df.merge(self.flows_df, on='name')
        self.grid_data = self.grid_data.merge(self.conductor_df, left_on='conductor', right_on='ConductorName')
        self.grid_data = self.grid_data.merge(self.buses_df[['name', 'v_nom']], left_on='bus0', right_on='name', suffixes=('', '_bus'))
        
    def calculate_rating(self, conductor_name, mot, temp, wind):
        """Calculate IEEE 738 rating"""
        conductor_row = self.conductor_df[self.conductor_df['ConductorName'] == conductor_name].iloc[0]
        
        params = {
            'Ta': temp, 'WindVelocity': wind, 'TLo': 25, 'THi': 50,
            'RLo': conductor_row['RES_25C'] / 5280, 'RHi': conductor_row['RES_50C'] / 5280,
            'Diameter': conductor_row['CDRAD_in'] * 2, 'Tc': mot,
            'WindAngleDeg': 90, 'SunTime': 12, 'Date': '10 Oct',
            'Emissivity': 0.8, 'Absorptivity': 0.8, 'Direction': 'EastWest',
            'Atmosphere': 'Clear', 'Elevation': 1000, 'Latitude': 27
        }
        
        try:
            cp = ConductorParams(**params)
            conductor = ieee738.Conductor(cp)
            return conductor.steady_state_thermal_rating()
        except:
            return None
    
    def analyze_conditions(self, temp, wind):
        """Analyze grid under given conditions"""
        results = []
        critical_count = 0
        caution_count = 0
        normal_count = 0
        
        for _, line in self.grid_data.iterrows():
            rating_amps = self.calculate_rating(line['conductor'], line['MOT'], temp, wind)
            if rating_amps:
                rating_mva = np.sqrt(3) * rating_amps * line['v_nom'] * 1000 / 1e6
                loading = (line['p0_nominal'] / rating_mva) * 100
                
                if loading >= 90:
                    status = 'critical'
                    critical_count += 1
                elif loading >= 60:
                    status = 'caution'
                    caution_count += 1
                else:
                    status = 'normal'
                    normal_count += 1
                
                # Create a cleaner conductor display name
                conductor_display = line['conductor']
                if 'ACSR' in conductor_display:
                    # Extract the main size and bird code name
                    parts = conductor_display.split()
                    if len(parts) >= 4:  # e.g., "3/0 ACSR 6/1 PIGEON"
                        size = parts[0]  # "3/0" or "336.4"
                        bird_name = parts[-1]  # "PIGEON", "DOVE", etc.
                        conductor_display = f"{size} {bird_name}"
                    elif len(parts) >= 2:  # fallback
                        conductor_display = f"{parts[0]} {parts[-1]}"
                
                results.append({
                    'name': line['name'],
                    'branch_name': line['branch_name'],
                    'conductor': line['conductor'],
                    'conductor_display': conductor_display,
                    'voltage': line['v_nom'],
                    'flow': line['p0_nominal'],
                    'rating': rating_mva,
                    'loading': loading,
                    'status': status
                })
        
        return {
            'lines': sorted(results, key=lambda x: x['loading'], reverse=True),
            'summary': {
                'critical': critical_count,
                'caution': caution_count,
                'normal': normal_count,
                'total': len(results),
                'max_loading': max([r['loading'] for r in results]),
                'avg_loading': np.mean([r['loading'] for r in results])
            }
        }

# Initialize analyzer
analyzer = GridAnalyzer()

@app.route('/')
def index():
    """Main dashboard"""
    return render_template('index.html')

@app.route('/api/analyze')
def analyze():
    """API endpoint for grid analysis"""
    temp = float(request.args.get('temp', 35))
    wind = float(request.args.get('wind', 2.0))
    
    results = analyzer.analyze_conditions(temp, wind)
    return jsonify(results)

@app.route('/api/system_info')
def system_info():
    """Get basic system information"""
    return jsonify({
        'buses': len(analyzer.buses_df),
        'lines': len(analyzer.lines_df),
        'conductors': len(analyzer.conductor_df),
        'voltage_levels': sorted(analyzer.buses_df['v_nom'].unique().tolist()),
        'conductor_types': analyzer.conductor_df['ConductorName'].tolist()
    })

@app.route('/api/temperature_sweep')
def temperature_sweep():
    """Temperature sensitivity analysis"""
    wind = float(request.args.get('wind', 2.0))
    temps = range(25, 61, 5)
    
    results = []
    for temp in temps:
        analysis = analyzer.analyze_conditions(temp, wind)
        results.append({
            'temperature': temp,
            'critical': analysis['summary']['critical'],
            'caution': analysis['summary']['caution'],
            'normal': analysis['summary']['normal'],
            'max_loading': analysis['summary']['max_loading']
        })
    
    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)