#!/usr/bin/env python3
"""
Grid analyzer class and related functionality for the AEP Grid Challenge application.
"""

import pandas as pd
import numpy as np
import json
import pypsa
from aep_challenge_solution import AEPGridChallenge
from config import GIS_LINES_PATH, GIS_BUSES_PATH


class FlaskGridAnalyzer(AEPGridChallenge):
    """Flask wrapper for AEP Challenge solution"""
    
    def __init__(self):
        super().__init__()
        self.load_gis_data()
        
    def load_gis_data(self):
        """Load GIS data for mapping"""
        try:
            with open(GIS_LINES_PATH, 'r') as f:
                self.gis_lines = json.load(f)
            with open(GIS_BUSES_PATH, 'r') as f:
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
    
    def get_contingency_status(self, max_loading):
        """Determine contingency status based on maximum loading"""
        if max_loading >= 100:
            return 'OVERLOADED'
        elif max_loading >= 90:
            return 'CRITICAL'
        elif max_loading >= 60:
            return 'CAUTION'
        else:
            return 'NORMAL'    

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

    def run_enhanced_n1_contingency(self, ambient_temp=35, wind_speed=2.0, max_lines=None):
        """Enhanced N-1 Contingency Analysis for Flask interface"""
        try:
            # Load PyPSA network
            network = pypsa.Network()
            network.import_from_csv_folder('hawaii40_osu/csv')
            network.pf()
            
            violations = []
            contingency_results = []
            
            # Get list of lines to test
            lines_to_test = network.lines.index[:max_lines] if max_lines else network.lines.index
            
            for line_out in lines_to_test:
                # Create contingency network
                cont_network = network.copy()
                cont_network.lines.drop(line_out, inplace=True)
                
                try:
                    cont_network.pf()
                    
                    # Check post-contingency loadings
                    flows = cont_network.lines_t.p0.iloc[0]
                    line_violations = []
                    max_loading = 0
                    
                    for line_name, flow in flows.items():
                        if line_name in self.grid_data['name'].values:
                            line_data = self.grid_data[self.grid_data['name'] == line_name].iloc[0]
                            rating_amps = self.calculate_dynamic_rating(line_data['conductor'], line_data['MOT'], ambient_temp, wind_speed)
                            
                            if rating_amps:
                                rating_mva = np.sqrt(3) * rating_amps * line_data['v_nom'] * 1000 / 1e6
                                loading_pct = (abs(flow) / rating_mva) * 100
                                max_loading = max(max_loading, loading_pct)
                                
                                if loading_pct > 80:
                                    line_violations.append({
                                        'line_name': str(line_name),
                                        'branch_name': str(line_data['branch_name']),
                                        'loading_pct': float(loading_pct),
                                        'flow': float(abs(flow)),
                                        'rating': float(rating_mva),
                                        'conductor': str(line_data['conductor']),
                                        'voltage': float(line_data['v_nom']),
                                        'bus0': str(line_data['bus0']),
                                        'bus1': str(line_data['bus1'])
                                    })  
                  
                    # Store contingency result
                    contingency_results.append({
                        'contingency_line': str(line_out),
                        'contingency_name': str(self.grid_data[self.grid_data['name'] == line_out]['branch_name'].iloc[0]) if line_out in self.grid_data['name'].values else str(line_out),
                        'violations': line_violations,
                        'violation_count': int(len(line_violations)),
                        'max_loading': float(max_loading),
                        'status': self.get_contingency_status(max_loading) if len(line_violations) > 0 else 'NORMAL'
                    })
                    
                    # Add to violations list
                    for violation in line_violations:
                        violations.append({
                            'contingency': str(line_out),
                            'contingency_name': str(contingency_results[-1]['contingency_name']),
                            'overloaded_line': str(violation['line_name']),
                            'overloaded_line_name': str(violation['branch_name']),
                            'loading_pct': float(violation['loading_pct']),
                            'flow': float(violation['flow']),
                            'rating': float(violation['rating']),
                            'conductor': str(violation['conductor']),
                            'voltage': float(violation['voltage']),
                            'bus0': str(violation['bus0']),
                            'bus1': str(violation['bus1'])
                        })
                        
                except Exception as e:
                    contingency_results.append({
                        'contingency_line': str(line_out),
                        'contingency_name': str(self.grid_data[self.grid_data['name'] == line_out]['branch_name'].iloc[0]) if line_out in self.grid_data['name'].values else str(line_out),
                        'violations': [],
                        'violation_count': int(0),
                        'max_loading': float(0),
                        'status': 'ERROR',
                        'error': str(e)
                    })
                    continue
            
            return {
                'violations': sorted(violations, key=lambda x: x['loading_pct'], reverse=True),
                'contingency_results': sorted(contingency_results, key=lambda x: x['violation_count'], reverse=True),
                'summary': {
                    'total_contingencies': int(len(contingency_results)),
                    'critical_contingencies': int(len([c for c in contingency_results if c['status'] == 'CRITICAL'])),
                    'total_violations': int(len(violations)),
                    'temperature': float(ambient_temp),
                    'wind_speed': float(wind_speed)
                }
            }
            
        except Exception as e:
            return {
                'error': f'N-1 analysis failed: {str(e)}',
                'violations': [],
                'contingency_results': [],
                'summary': {
                    'total_contingencies': int(0),
                    'critical_contingencies': int(0),
                    'total_violations': int(0),
                    'temperature': float(ambient_temp),
                    'wind_speed': float(wind_speed)
                }
            }