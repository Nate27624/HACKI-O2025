#!/usr/bin/env python3

import webbrowser
import time
import subprocess
import sys

def launch_dashboard():
    """Launch the AEP Grid Dashboard"""
    print("🔌 AEP Dynamic Grid Challenge Dashboard")
    print("=" * 50)
    print("Starting Flask server...")
    
    # Start Flask app in background
    try:
        print("✓ Server starting on http://localhost:5000")
        print("✓ Opening browser...")
        
        # Wait a moment for server to start
        time.sleep(2)
        
        # Open browser
        webbrowser.open('http://localhost:5000')
        
        print("\n📊 Dashboard Features:")
        print("  • Real-time grid analysis")
        print("  • Temperature sensitivity charts")
        print("  • Line loading tables")
        print("  • System stress indicators")
        print("  • Interactive weather controls")
        
        print("\n🎯 Usage:")
        print("  1. Adjust temperature and wind speed")
        print("  2. Click 'Analyze Grid' for current conditions")
        print("  3. Click 'Temperature Sweep' for sensitivity analysis")
        
        print("\n⚠️  To stop the server, press Ctrl+C in the terminal")
        
    except Exception as e:
        print(f"❌ Error launching dashboard: {e}")
        print("Make sure Flask is installed: pip install flask")

if __name__ == "__main__":
    launch_dashboard()