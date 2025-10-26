#!/usr/bin/env python3
"""
API route handlers for the AEP Grid Challenge application.
"""

from flask import request, jsonify
import numpy as np
from utils import update_weather_conditions
from ai_service import generate_ai_summary


def register_api_routes(app, analyzer):
    """Register all API routes with the Flask app"""
    
    @app.route('/api/analyze')
    def analyze():
        """API endpoint for grid analysis"""
        temp = float(request.args.get('temp', 35))
        wind = float(request.args.get('wind', 2.0))
        
        # Update global weather conditions for AI analysis
        update_weather_conditions(temp=temp, wind=wind, conditions='Variable')
        
        results = analyzer.analyze_conditions(temp, wind)
        return jsonify(results)

    @app.route('/api/gis_data')
    def gis_data():
        """Get GIS data with loading information"""
        temp = float(request.args.get('temp', 35))
        wind = float(request.args.get('wind', 2.0))
        
        # Update global weather conditions for AI analysis
        update_weather_conditions(temp=temp, wind=wind, conditions='Variable')
        
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

    @app.route('/api/n1_analysis')
    def n1_analysis():
        """N-1 Contingency Analysis API endpoint"""
        temp = float(request.args.get('temp', 35))
        wind = float(request.args.get('wind', 2.0))
        max_lines = request.args.get('max_lines', None)
        
        if max_lines:
            max_lines = int(max_lines)
        
        results = analyzer.run_enhanced_n1_contingency(temp, wind, max_lines)
        return jsonify(results)

    @app.route('/api/ai-summary', methods=['POST'])
    def get_ai_summary():
        """Generate AI summary and recommendations using Google Gemini"""
        try:
            # Get request data
            data = request.get_json()
            summary_type = data.get('type', 'dashboard')  # 'dashboard' or 'n1'
            n1_results = data.get('n1_results', None)  # Optional N-1 results from frontend
            
            # Generate AI summary
            result = generate_ai_summary(analyzer, summary_type, n1_results)
            
            if result['success']:
                return jsonify(result)
            else:
                return jsonify(result), 400 if 'not configured' in result['error'] else 500
                
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'AI summary generation failed: {str(e)}'
            }), 500