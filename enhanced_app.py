#!/usr/bin/env python3
"""
Legacy entry point for the AEP Grid Challenge application.
This file now imports from the refactored modular structure.
For new development, use main.py or run_app.py instead.
"""

# Import the refactored application components
from main import app, analyzer
from utils import grid_nodes, weather_conditions, update_global_data
from grid_analyzer import FlaskGridAnalyzer
from ai_service import collect_system_data, create_dashboard_summary_prompt, create_n1_analysis_prompt

# Maintain backward compatibility by exposing the same interface
__all__ = [
    'app', 
    'analyzer', 
    'grid_nodes', 
    'weather_conditions',
    'FlaskGridAnalyzer',
    'update_global_data',
    'collect_system_data',
    'create_dashboard_summary_prompt',
    'create_n1_analysis_prompt'
]

if __name__ == '__main__':
    # Run the application if this file is executed directly
    from config import FLASK_CONFIG
    print("Running AEP Grid Challenge Application (legacy entry point)")
    print("Consider using 'python main.py' or 'python run_app.py' for new development")
    app.run(**FLASK_CONFIG)