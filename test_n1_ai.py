#!/usr/bin/env python3
"""
Test script to verify N-1 AI data collection is working properly.
"""

from grid_analyzer import FlaskGridAnalyzer
from ai_service import collect_system_data, create_n1_analysis_prompt
from utils import update_global_data, update_weather_conditions

def test_n1_data_collection():
    """Test that N-1 AI gets proper contingency data"""
    print("Testing N-1 AI data collection...")
    
    # Initialize analyzer
    analyzer = FlaskGridAnalyzer()
    update_global_data(analyzer)
    
    # Set test conditions
    update_weather_conditions(temp=35, wind=2.0)
    
    # Test base case data collection
    print("\n1. Testing base case data collection:")
    base_data = collect_system_data(analyzer, 'dashboard')
    print(f"   Base case overloaded lines: {base_data['system_status']['overloaded_count']}")
    print(f"   Base case critical lines: {base_data['system_status']['critical_count']}")
    print(f"   Has N-1 data: {'n1_data' in base_data}")
    
    # Test N-1 data collection
    print("\n2. Testing N-1 data collection:")
    n1_data = collect_system_data(analyzer, 'n1')
    print(f"   Base case overloaded lines: {n1_data['system_status']['overloaded_count']}")
    print(f"   Base case critical lines: {n1_data['system_status']['critical_count']}")
    print(f"   Has N-1 data: {'n1_data' in n1_data}")
    
    if 'n1_data' in n1_data:
        n1_summary = n1_data['n1_data']['summary']
        print(f"   N-1 total contingencies: {n1_summary.get('total_contingencies', 0)}")
        print(f"   N-1 critical contingencies: {n1_summary.get('critical_contingencies', 0)}")
        print(f"   N-1 total violations: {n1_summary.get('total_violations', 0)}")
        
        # Test prompt generation
        print("\n3. Testing N-1 prompt generation:")
        prompt = create_n1_analysis_prompt(n1_data)
        if "N-1 CONTINGENCY ANALYSIS RESULTS:" in prompt:
            print("   ✅ Prompt includes N-1 analysis results")
        else:
            print("   ❌ Prompt missing N-1 analysis results")
            
        if f"Total Contingencies Tested: {n1_summary.get('total_contingencies', 0)}" in prompt:
            print("   ✅ Prompt includes contingency count")
        else:
            print("   ❌ Prompt missing contingency count")
    else:
        print("   ❌ N-1 data collection failed")

if __name__ == '__main__':
    test_n1_data_collection()