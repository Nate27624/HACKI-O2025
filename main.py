#!/usr/bin/env python3
"""
Main Flask application for the AEP Grid Challenge.
"""

from flask import Flask, render_template
from grid_analyzer import FlaskGridAnalyzer
from api_routes import register_api_routes
from utils import update_global_data
from config import FLASK_CONFIG

# Initialize Flask app
app = Flask(__name__)

# Initialize analyzer with AEP solution
analyzer = FlaskGridAnalyzer()

# Initialize global data
update_global_data(analyzer)

# Register API routes
register_api_routes(app, analyzer)


@app.route('/')
def index():
    """Main dashboard"""
    return render_template('enhanced_dashboard.html')


@app.route('/n1')
def n1_contingency():
    """N-1 Contingency Analysis dashboard"""
    return render_template('n1_dashboard.html')


if __name__ == '__main__':
    app.run(**FLASK_CONFIG)