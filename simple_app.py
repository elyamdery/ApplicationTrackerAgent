"""
Simple Application Entry Point
A simplified version of the application to test if our refactoring works.
"""

import os
import sys
import logging

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from flask import Flask, render_template

app = Flask(__name__, 
           static_folder='app/web/static', 
           template_folder='app/web/templates')

@app.route('/')
def index():
    return render_template('index.html', 
                          applications=[],
                          is_authenticated=False,
                          monitored_email="example@gmail.com",
                          last_scan_time=None)

@app.route('/settings')
def settings():
    return render_template('settings.html', 
                          email="example@gmail.com",
                          monitored_email="example@gmail.com",
                          has_token_file=False,
                          credentials_valid=False,
                          is_authenticated=False)

@app.route('/auth_status')
def auth_status():
    auth_info = {
        'has_token_file': False,
        'credentials_valid': False,
        'session_contains_state': False,
        'session_keys': [],
        'redirect_uri': 'http://localhost:8080/oauth2callback'
    }
    return render_template('auth_status.html', auth_info=auth_info)

@app.route('/error')
def error():
    return render_template('error.html', 
                          error="Test error",
                          message="This is a test error message")

if __name__ == '__main__':
    logger.info("Starting simplified Flask application")
    app.run(host='0.0.0.0', port=8080, debug=True)
