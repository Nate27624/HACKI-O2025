#!/usr/bin/env python3
"""
AI service functionality for generating summaries and recommendations.
"""

from datetime import datetime
from utils import get_global_weather_conditions, get_global_grid_nodes
from config import GEMINI_API_KEY


def collect_system_data(analyzer, analysis_type='dashboard', n1_results=None):
    """Collect current system data for AI analysis"""
    try:
        # Check if analyzer is available
        if analyzer is None:
            return {'error': 'Grid analyzer not available'}
        
        # Get current weather conditions
        weather_conditions = get_global_weather_conditions()
        temp = weather_conditions.get('temperature', 35)
        wind = weather_conditions.get('wind_speed', 2.0)
        
        # Get real grid analysis data
        analysis = analyzer.analyze_conditions(temp, wind)
        
        # For N-1 analysis, use provided results or run new analysis
        n1_data = None
        if analysis_type == 'n1':
            if n1_results:
                # Use provided N-1 results from frontend
                n1_data = n1_results
            else:
                # Fallback: run new N-1 analysis
                n1_data = analyzer.run_enhanced_n1_contingency(temp, wind)
        
        # Get weather data
        weather_data = {
            'temperature': temp,
            'humidity': weather_conditions.get('humidity', 60),
            'wind_speed': wind,
            'conditions': weather_conditions.get('conditions', 'Clear')
        }
        
        # Extract line data with actual loading information
        lines_data = []
        overloaded_lines = []
        critical_lines = []
        caution_lines = []
        normal_lines = []
        
        for line in analysis.get('lines', []):
            loading = line.get('loading', 0)
            line_info = {
                'name': line.get('name', 'Unknown'),
                'branch_name': line.get('branch_name', 'Unknown'),
                'loading': loading,
                'flow': line.get('flow', 0),
                'rating': line.get('rating', 0),
                'voltage': line.get('voltage', 0),
                'conductor': line.get('conductor', 'Unknown'),
                'bus0': line.get('bus0', ''),
                'bus1': line.get('bus1', ''),
                'status': 'Overloaded' if loading > 100 else 'Critical' if loading > 90 else 'Caution' if loading > 75 else 'Normal'
            }
            lines_data.append(line_info)       
     
            if loading > 100:
                overloaded_lines.append(line_info)
            elif loading > 90:
                critical_lines.append(line_info)
            elif loading > 75:
                caution_lines.append(line_info)
            else:
                normal_lines.append(line_info)
        
        # Get system summary
        summary = analysis.get('summary', {})
        max_loading = max([line.get('loading', 0) for line in analysis.get('lines', [])], default=0)
        avg_loading = sum([line.get('loading', 0) for line in analysis.get('lines', [])]) / len(analysis.get('lines', [])) if analysis.get('lines') else 0
        
        # Find most loaded line
        most_loaded_line = max(analysis.get('lines', []), key=lambda x: x.get('loading', 0), default={})
        
        # Prepare return data
        result = {
            'weather_data': weather_data,
            'system_status': {
                'overall_status': 'OVERLOADED' if len(overloaded_lines) > 0 else 'CRITICAL' if len(critical_lines) > 0 else 'CAUTION' if len(caution_lines) > 0 else 'NORMAL',
                'max_loading': max_loading,
                'avg_loading': avg_loading,
                'total_lines': len(lines_data),
                'overloaded_count': len(overloaded_lines),
                'critical_count': len(critical_lines),
                'caution_count': len(caution_lines),
                'normal_count': len(normal_lines)
            },
            'lines_data': lines_data,
            'overloaded_lines': overloaded_lines,
            'critical_lines': critical_lines,
            'most_loaded_line': most_loaded_line,
            'summary': summary,
            'timestamp': datetime.now().isoformat()
        }
        
        # Add N-1 specific data if available
        if n1_data and 'error' not in n1_data:
            result['n1_data'] = {
                'violations': n1_data.get('violations', []),
                'contingency_results': n1_data.get('contingency_results', []),
                'summary': n1_data.get('summary', {}),
                'total_contingencies': n1_data.get('summary', {}).get('total_contingencies', 0),
                'critical_contingencies': n1_data.get('summary', {}).get('critical_contingencies', 0),
                'total_violations': n1_data.get('summary', {}).get('total_violations', 0)
            }
            
            # Update system status based on N-1 results if more severe
            n1_violations = len(n1_data.get('violations', []))
            n1_critical_contingencies = n1_data.get('summary', {}).get('critical_contingencies', 0)
            
            if n1_violations > 0 or n1_critical_contingencies > 0:
                if result['system_status']['overall_status'] in ['NORMAL', 'CAUTION']:
                    result['system_status']['overall_status'] = 'CRITICAL'
        
        return result
    except Exception as e:
        return {'error': str(e)}


def create_dashboard_summary_prompt(data):
    """Create prompt for dashboard summary"""
    try:
        system_status = data.get('system_status', {})
        weather_data = data.get('weather_data', {})
        overloaded_lines = data.get('overloaded_lines', [])
        critical_lines = data.get('critical_lines', [])
        most_loaded_line = data.get('most_loaded_line', {})
        
        return f"""
You are an expert electrical grid analyst. Analyze the following REAL power grid data and provide a comprehensive summary with actionable recommendations.

CURRENT SYSTEM STATUS: {system_status.get('overall_status', 'UNKNOWN')}
- Temperature: {weather_data.get('temperature', 'N/A')}°C
- Wind Speed: {weather_data.get('wind_speed', 'N/A')} ft/sec
- Total Lines: {system_status.get('total_lines', 0)}
- Overloaded Lines: {system_status.get('overloaded_count', 0)} (>100%)
- Critical Lines: {system_status.get('critical_count', 0)} (90-100%)
- Caution Lines: {system_status.get('caution_count', 0)} (75-90%)
- Normal Lines: {system_status.get('normal_count', 0)} (<75%)
- Maximum Loading: {system_status.get('max_loading', 0):.1f}%
- Average Loading: {system_status.get('avg_loading', 0):.1f}%

MOST LOADED LINE:
- Name: {most_loaded_line.get('name', 'N/A')} ({most_loaded_line.get('branch_name', 'N/A')})
- Loading: {most_loaded_line.get('loading', 0):.1f}%
- Flow: {most_loaded_line.get('flow', 0):.1f} MW
- Rating: {most_loaded_line.get('rating', 0):.1f} MW
- Connection: {most_loaded_line.get('bus0', '')} → {most_loaded_line.get('bus1', '')}

OVERLOADED LINES (>100%):
{chr(10).join([f"- {line.get('name', 'Unknown')} ({line.get('branch_name', 'Unknown')}): {line.get('loading', 0):.1f}% loading" for line in overloaded_lines[:10]]) if overloaded_lines else "None"}

CRITICAL LINES (90-100%):
{chr(10).join([f"- {line.get('name', 'Unknown')} ({line.get('branch_name', 'Unknown')}): {line.get('loading', 0):.1f}% loading" for line in critical_lines[:5]]) if critical_lines else "None"}

Please provide:
1. **System Health Summary** - Overall assessment based on the {system_status.get('overloaded_count', 0)} overloaded lines
2. **Critical Issues** - Immediate concerns about overloaded and critical lines
3. **Weather Impact Analysis** - How {weather_data.get('temperature', 'N/A')}°C temperature affects line ratings
4. **Immediate Recommendations** - Actions to reduce overloads and prevent cascading failures
5. **Preventive Measures** - Long-term solutions for grid reliability

Focus on the REAL overload situation with {system_status.get('overloaded_count', 0)} lines exceeding 100% capacity.
"""
    except Exception as e:
        return f"Error creating prompt: {str(e)}"


def create_n1_analysis_prompt(data):
    """Create prompt for N-1 contingency analysis"""
    try:
        system_status = data.get('system_status', {})
        weather_data = data.get('weather_data', {})
        overloaded_lines = data.get('overloaded_lines', [])
        critical_lines = data.get('critical_lines', [])
        most_loaded_line = data.get('most_loaded_line', {})
        n1_data = data.get('n1_data', {})
        
        # Get N-1 specific data
        n1_violations = n1_data.get('violations', [])
        n1_summary = n1_data.get('summary', {})
        contingency_results = n1_data.get('contingency_results', [])
        
        # Get worst N-1 violations
        worst_violations = sorted(n1_violations, key=lambda x: x.get('loading_pct', 0), reverse=True)[:10]
        critical_contingencies = [c for c in contingency_results if c.get('status') == 'CRITICAL'][:10]
        
        return f"""
You are an electrical grid reliability analyst. Analyze the following REAL N-1 contingency analysis results.

BASE CASE SYSTEM STATUS: {system_status.get('overall_status', 'UNKNOWN')}
- Temperature: {weather_data.get('temperature', 'N/A')}°C (affects line thermal ratings)
- Wind Speed: {weather_data.get('wind_speed', 'N/A')} ft/sec (affects line cooling)
- Base Case Overloaded Lines: {system_status.get('overloaded_count', 0)} (>100%)
- Base Case Critical Lines: {system_status.get('critical_count', 0)} (90-100%)
- Base Case Max Loading: {system_status.get('max_loading', 0):.1f}%

N-1 CONTINGENCY ANALYSIS RESULTS:
- Total Contingencies Tested: {n1_summary.get('total_contingencies', 0)}
- Critical Contingencies: {n1_summary.get('critical_contingencies', 0)} (cause violations)
- Total N-1 Violations: {n1_summary.get('total_violations', 0)} (lines >80% post-contingency)

WORST N-1 VIOLATIONS (Post-Contingency Overloads):
{chr(10).join([f"- Contingency: {v.get('contingency_name', 'Unknown')} → Overloads {v.get('overloaded_line_name', 'Unknown')}: {v.get('loading_pct', 0):.1f}% loading" for v in worst_violations[:10]]) if worst_violations else "None"}

CRITICAL CONTINGENCIES (Cause Multiple Violations):
{chr(10).join([f"- {c.get('contingency_name', 'Unknown')}: {c.get('violation_count', 0)} violations, max {c.get('max_loading', 0):.1f}% loading" for c in critical_contingencies[:5]]) if critical_contingencies else "None"}

MOST LOADED LINE IN BASE CASE (Highest N-1 Risk):
- {most_loaded_line.get('name', 'N/A')} ({most_loaded_line.get('branch_name', 'N/A')})
- Base Loading: {most_loaded_line.get('loading', 0):.1f}%
- Flow: {most_loaded_line.get('flow', 0):.1f} MW / {most_loaded_line.get('rating', 0):.1f} MW rating

Please provide an N-1 CONTINGENCY ANALYSIS focusing on the REAL N-1 violations:

1. **N-1 Compliance Status** - Assessment of the {n1_summary.get('critical_contingencies', 0)} critical contingencies
2. **Worst Case Scenarios** - Analysis of the {len(worst_violations)} most severe N-1 violations  
3. **System Vulnerabilities** - Which contingencies cause the most widespread problems?
4. **Cascade Risk Assessment** - How N-1 violations could lead to cascading failures
5. **Emergency Response** - Immediate actions for the {n1_summary.get('critical_contingencies', 0)} critical contingencies
6. **System Reinforcement** - Long-term solutions to improve N-1 compliance

Focus on the REAL N-1 analysis results showing {n1_summary.get('total_violations', 0)} post-contingency violations.
"""
    except Exception as e:
        return f"Error creating N-1 prompt: {str(e)}"


def generate_ai_summary(analyzer, summary_type='dashboard', n1_results=None):
    """Generate AI summary using Google Gemini"""
    try:
        import google.generativeai as genai
        
        # Configure Gemini API
        if GEMINI_API_KEY == 'YOUR_GEMINI_API_KEY_HERE':
            return {
                'success': False,
                'error': 'Gemini API key not configured. Please set GEMINI_API_KEY environment variable.'
            }
        
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Collect current system data
        current_data = collect_system_data(analyzer, summary_type, n1_results)
        
        # Check if data collection failed
        if 'error' in current_data:
            return {
                'success': False,
                'error': f'Failed to collect system data: {current_data["error"]}'
            }
        
        # Create context-specific prompt
        if summary_type == 'n1':
            prompt = create_n1_analysis_prompt(current_data)
        else:
            prompt = create_dashboard_summary_prompt(current_data)
        
        # Generate AI response
        response = model.generate_content(prompt)
        
        return {
            'success': True,
            'summary': response.text,
            'timestamp': datetime.now().isoformat()
        }
        
    except ImportError:
        return {
            'success': False,
            'error': 'Google Generative AI library not installed. Run: pip install google-generativeai'
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'AI summary generation failed: {str(e)}'
        }