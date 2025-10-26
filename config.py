#!/usr/bin/env python3
"""
Configuration and constants for the AEP Grid Challenge application.
"""

import warnings
warnings.filterwarnings('ignore')

# Flask configuration
FLASK_CONFIG = {
    'debug': True,
    'host': '0.0.0.0',
    'port': 5001
}

# Global variables for AI analysis
INITIAL_GRID_NODES = []
INITIAL_WEATHER_CONDITIONS = {
    'temperature': 75,
    'humidity': 60,
    'wind_speed': 10,
    'conditions': 'Clear'
}

# GIS data file paths
GIS_LINES_PATH = 'hawaii40_osu/gis/oneline_lines.geojson'
GIS_BUSES_PATH = 'hawaii40_osu/gis/oneline_busses.geojson'

# Gemini API configuration
GEMINI_API_KEY = "AIzaSyB5ZEuZ1US3T6UubRLuRmGV3e3dkhLx66o"