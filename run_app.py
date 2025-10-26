#!/usr/bin/env python3
"""
Application runner - use this to start the refactored AEP Grid Challenge application.
"""

if __name__ == '__main__':
    from main import app
    from config import FLASK_CONFIG
    
    print("Starting AEP Grid Challenge Application...")
    print(f"Server will be available at: http://localhost:{FLASK_CONFIG['port']}")
    print("Press Ctrl+C to stop the server")
    
    app.run(**FLASK_CONFIG)