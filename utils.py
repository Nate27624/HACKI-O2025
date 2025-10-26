#!/usr/bin/env python3
"""
Utility functions and global data management for the AEP Grid Challenge application.
"""

import numpy as np
from config import INITIAL_GRID_NODES, INITIAL_WEATHER_CONDITIONS

# Initialize global variables for AI analysis
grid_nodes = []
weather_conditions = INITIAL_WEATHER_CONDITIONS.copy()


def update_global_data(analyzer):
    """Update global variables with current grid data"""
    global grid_nodes, weather_conditions
    
    # Convert grid data to nodes format for AI analysis
    grid_nodes.clear()
    if hasattr(analyzer, 'grid_data') and analyzer.grid_data is not None:
        # Group lines by major areas/substations for node representation
        node_groups = {}
        for _, line in analyzer.grid_data.iterrows():
            # Extract area/substation from branch name
            branch_name = str(line.get('branch_name', line.get('name', 'Unknown')))
            area_name = branch_name.split('-')[0].strip() if '-' in branch_name else branch_name[:15]
            
            if area_name not in node_groups:
                node_groups[area_name] = {
                    'total_load': 0,
                    'total_capacity': 0,
                    'line_count': 0,
                    'voltage_levels': []
                }
            
            # Aggregate data for this area
            node_groups[area_name]['total_load'] += float(line.get('p0_nominal', 0))
            node_groups[area_name]['total_capacity'] += float(line.get('MOT', 100))
            node_groups[area_name]['line_count'] += 1
            node_groups[area_name]['voltage_levels'].append(float(line.get('v_nom', 138)))
        
        # Create nodes from grouped data
        for area_name, data in node_groups.items():
            avg_voltage = np.mean(data['voltage_levels']) if data['voltage_levels'] else 138
            grid_nodes.append({
                'name': area_name,
                'load': round(data['total_load'], 1),
                'capacity': round(data['total_capacity'], 1),
                'voltage': round(avg_voltage, 1),
                'line_count': data['line_count']
            })
    
    # If no grid data, create realistic Hawaii grid sample data
    if not grid_nodes:
        grid_nodes.extend([
            {'name': 'Honolulu Central', 'load': 185.5, 'capacity': 220.0, 'voltage': 138, 'line_count': 8},
            {'name': 'Pearl Harbor', 'load': 142.3, 'capacity': 180.0, 'voltage': 138, 'line_count': 6},
            {'name': 'Waipahu', 'load': 98.7, 'capacity': 130.0, 'voltage': 138, 'line_count': 4},
            {'name': 'Keehi', 'load': 156.2, 'capacity': 200.0, 'voltage': 138, 'line_count': 7},
            {'name': 'Iwilei', 'load': 89.4, 'capacity': 110.0, 'voltage': 138, 'line_count': 3},
            {'name': 'Kalihi', 'load': 67.8, 'capacity': 90.0, 'voltage': 138, 'line_count': 3}
        ])


def get_global_weather_conditions():
    """Get current global weather conditions"""
    return weather_conditions


def update_weather_conditions(temp=None, wind=None, conditions=None):
    """Update global weather conditions"""
    global weather_conditions
    if temp is not None:
        weather_conditions['temperature'] = temp
    if wind is not None:
        weather_conditions['wind_speed'] = wind
    if conditions is not None:
        weather_conditions['conditions'] = conditions


def get_global_grid_nodes():
    """Get current global grid nodes"""
    return grid_nodes