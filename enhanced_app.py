#!/usr/bin/env python3

from flask import Flask, render_template, request, jsonify
import pandas as pd
import numpy as np
import json
import sys
import warnings
import pypsa
warnings.filterwarnings('ignore')

# Import the exact AEP Challenge solution
from aep_challenge_solution import AEPGridChallenge

app = Flask(__name__)

class FlaskGridAnalyzer(AEPGridChallenge):
    """Flask wrapper for AEP Challenge solution"""
    
    def __init__(self):
        super().__init__()
        self.load_gis_data()
        
    def load_gis_data(self):
        """Load GIS data for mapping"""
        try:
            with open('hawaii40_osu/gis/oneline_lines.geojson', 'r') as f:
                self.gis_lines = json.load(f)
            with open('hawaii40_osu/gis/oneline_busses.geojson', 'r') as f:
                self.gis_buses = json.load(f)
        except:
            self.gis_lines = None
            self.gis_buses = None
    
    def analyze_conditions(self, temp, wind):
        """Analyze grid conditions using AEP solution methods"""
        results = []
        critical_count = 0
        caution_count = 0
        normal_count = 0
        
        for _, line in self.grid_data.iterrows():
            rating_amps = self.calculate_dynamic_rating(line['conductor'], line['MOT'], temp, wind)
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
                
                results.append({
                    'name': line['name'],
                    'branch_name': line['branch_name'],
                    'conductor': line['conductor'],
                    'voltage': line['v_nom'],
                    'flow': line['p0_nominal'],
                    'rating': rating_mva,
                    'loading': loading,
                    'status': status,
                    'bus0': line['bus0'],
                    'bus1': line['bus1']
                })
        
        return {
            'lines': sorted(results, key=lambda x: x['loading'], reverse=True),
            'summary': {
                'critical': critical_count,
                'caution': caution_count,
                'normal': normal_count,
                'total': len(results),
                'max_loading': max([r['loading'] for r in results]) if results else 0,
                'avg_loading': np.mean([r['loading'] for r in results]) if results else 0
            }
        }
    
    def get_gis_data(self, temp, wind):
        """Get GIS data with loading information for interactive map"""
        if not self.gis_lines:
            return None
            
        analysis = self.analyze_conditions(temp, wind)
        line_loadings = {line['name']: line for line in analysis['lines']}
        
        # Create a copy to avoid modifying original
        gis_data = json.loads(json.dumps(self.gis_lines))
        
        # Add loading info to GIS features
        for feature in gis_data['features']:
            line_name = feature['properties'].get('Name', '')
            if line_name in line_loadings:
                loading_info = line_loadings[line_name]
                feature['properties']['loading'] = loading_info['loading']
                feature['properties']['status'] = loading_info['status']
                feature['properties']['rating'] = loading_info['rating']
                feature['properties']['flow'] = loading_info['flow']
                feature['properties']['conductor'] = loading_info['conductor']
            else:
                # Default values for lines without data
                feature['properties']['loading'] = 0
                feature['properties']['status'] = 'normal'
                feature['properties']['rating'] = 0
                feature['properties']['flow'] = 0
        
        return gis_data
    
    def get_challenge_results(self):
        """Get the key challenge results"""
        critical_temp = self.find_critical_temperature()
        critical_lines = self.identify_critical_lines(50)
        
        # System stress at different temperatures
        stress_results = []
        for temp in [30, 40, 50, 60]:
            stress = self.assess_system_stress(temp)
            status = "CRITICAL" if stress['critical_lines'] > 0 else "CAUTION" if stress['caution_lines'] > 5 else "NORMAL"
            stress_results.append({
                'temperature': temp,
                'status': status,
                'critical': stress['critical_lines'],
                'caution': stress['caution_lines'],
                'normal': stress['normal_lines']
            })
        
        return {
            'critical_temperature': critical_temp,
            'most_critical_lines': critical_lines.head(5).to_dict('records'),
            'stress_progression': stress_results
        }

# Initialize analyzer with AEP solution
analyzer = FlaskGridAnalyzer()

@app.route('/')
def index():
    """Main dashboard"""
    return render_template('enhanced_dashboard.html')

@app.route('/map')
def map_view():
    """Map-only dashboard"""
    return render_template('map_dashboard.html')

@app.route('/api/analyze')
def analyze():
    """API endpoint for grid analysis"""
    temp = float(request.args.get('temp', 35))
    wind = float(request.args.get('wind', 2.0))
    
    results = analyzer.analyze_conditions(temp, wind)
    return jsonify(results)

@app.route('/api/gis_data')
def gis_data():
    """Get GIS data with loading information"""
    temp = float(request.args.get('temp', 35))
    wind = float(request.args.get('wind', 2.0))
    
    gis_data = analyzer.get_gis_data(temp, wind)
    if gis_data:
        return jsonify(gis_data)
    else:
        return jsonify({'error': 'GIS data not available'})

@app.route('/api/temperature_sweep')
def temperature_sweep():
    """Temperature sensitivity analysis using AEP solution"""
    wind = float(request.args.get('wind', 2.0))
    
    # Use the exact method from AEP solution
    temp_results = analyzer.analyze_temperature_impact((25, 60), wind)
    
    results = []
    for _, row in temp_results.iterrows():
        analysis = analyzer.analyze_conditions(row['temperature'], wind)
        results.append({
            'temperature': row['temperature'],
            'critical': analysis['summary']['critical'],
            'caution': analysis['summary']['caution'],
            'normal': analysis['summary']['normal'],
            'max_loading': row['max_loading'],
            'overloaded_lines': row['overloaded_lines']
        })
    
    return jsonify(results)

@app.route('/api/conductor_analysis')
def conductor_analysis():
    """Analyze by conductor type using AEP solution"""
    temp = float(request.args.get('temp', 50))
    wind = float(request.args.get('wind', 2.0))
    
    analysis = analyzer.analyze_conditions(temp, wind)
    
    # Group by conductor type
    conductor_stats = {}
    for line in analysis['lines']:
        conductor = line['conductor']
        if conductor not in conductor_stats:
            conductor_stats[conductor] = {
                'count': 0,
                'max_loading': 0,
                'avg_loading': 0,
                'overloaded': 0,
                'loadings': []
            }
        
        conductor_stats[conductor]['count'] += 1
        conductor_stats[conductor]['loadings'].append(line['loading'])
        conductor_stats[conductor]['max_loading'] = max(conductor_stats[conductor]['max_loading'], line['loading'])
        if line['loading'] > 100:
            conductor_stats[conductor]['overloaded'] += 1
    
    # Calculate averages
    for conductor in conductor_stats:
        conductor_stats[conductor]['avg_loading'] = np.mean(conductor_stats[conductor]['loadings'])
        del conductor_stats[conductor]['loadings']  # Remove raw data
    
    return jsonify(conductor_stats)

@app.route('/api/challenge_results')
def challenge_results():
    """Get the official AEP Challenge results"""
    return jsonify(analyzer.get_challenge_results())

@app.route('/api/find_first_overload')
def find_first_overload():
    """Find the first overload temperature and line details"""
    wind = float(request.args.get('wind', 2.0))
    
    # Find first overload with detailed line information
    for temp in range(25, 70):
        analysis = analyzer.analyze_conditions(temp, wind)
        
        # Find any overloaded lines (>100%)
        overloaded_lines = [line for line in analysis['lines'] if line['loading'] > 100]
        
        if overloaded_lines:
            # Get the most overloaded line
            most_overloaded = max(overloaded_lines, key=lambda x: x['loading'])
            
            return jsonify({
                'critical_temperature': temp,
                'first_overload_line': {
                    'name': most_overloaded['name'],
                    'branch_name': most_overloaded['branch_name'],
                    'conductor': most_overloaded['conductor'],
                    'voltage': most_overloaded['voltage'],
                    'loading': most_overloaded['loading'],
                    'flow': most_overloaded['flow'],
                    'rating': most_overloaded['rating'],
                    'bus0': most_overloaded['bus0'],
                    'bus1': most_overloaded['bus1']
                },
                'total_overloaded': len(overloaded_lines),
                'wind_speed': wind,
                'system_summary': analysis['summary']
            })
    
    # No overloads found in temperature range
    return jsonify({
        'critical_temperature': None,
        'message': 'No overloads found in temperature range 25-70°C',
        'wind_speed': wind
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)