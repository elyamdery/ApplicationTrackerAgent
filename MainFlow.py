import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Add the utils directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'utils'))

from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, session
import sqlite3
import csv
import logging
import pickle
import json
from apscheduler.schedulers.background import BackgroundScheduler
import openai
from datetime import datetime, timedelta
from collections import Counter
import atexit  # Add this import
from agents.email_monitor import EmailMonitorAgent
from services.gmail_service import GmailService
from agents.classifier_agent import ClassifierAgent
from agents.database_agent import DatabaseAgent
from agents.notification_agent import NotificationAgent
from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from utils.db_utils import get_db_connection, init_db
import webbrowser
from urllib.parse import urlparse, parse_qs
import secrets  # Add this import
from flask.sessions import SecureCookieSessionInterface

# Add this near the top of your file, after imports
import os
import re
import base64
import pickle
import logging
import threading
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

# Only set this environment variable in development, NEVER in production
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# For development only - allows OAuth over HTTP 
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Load environment variables from .env file
load_dotenv()

# Retrieve environment variables
smtp_server = os.getenv('SMTP_SERVER')
smtp_port = int(os.getenv('SMTP_PORT'))
email_username = os.getenv('EMAIL_USERNAME')
email_password = os.getenv('EMAIL_PASSWORD')
openai_api_key = os.getenv('OPENAI_API_KEY')
google_client_id = os.getenv('GOOGLE_CLIENT_ID')
google_client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
google_redirect_uri = os.getenv('GOOGLE_REDIRECT_URI')
monitored_email = os.getenv('MONITORED_EMAIL')

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('oauth_flow.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static', static_url_path='/static')
# Use a fixed secret key instead of a random one that changes on restart
app.secret_key = os.environ.get('FLASK_SECRET_KEY', secrets.token_hex(16))
# Set session cookie parameters for better persistence
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour
app.session_interface = SecureCookieSessionInterface()

# Scan window defaults
DEFAULT_SCAN_WINDOW_DAYS = 7
WINDOW_PRESET_MAP = {
    'daily': 1,
    'weekly': 7
}
MAX_SCAN_LOG_RETURN = 100

JOB_TYPE_OVERRIDES = {
    'workiz': 'Hybrid'
}

# Add these variables at the top level of your file
scan_status = {
    'is_scanning': False,
    'start_time': None,
    'end_time': None,
    'status': 'idle',  # idle, scanning, completed, error
    'result': None,
    'error': None,
    'window_days': DEFAULT_SCAN_WINDOW_DAYS,
    'updates': []
}


def _get_setting_value(key, default=None):
    """Lookup a setting value from the DB."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row['value'] if row else default
    except Exception as exc:
        logger.error(f"Error reading setting {key}: {exc}")
        return default
    finally:
        if conn:
            conn.close()


def _set_setting_value(key, value):
    """Persist a setting value to the DB."""
    conn = None
    try:
        conn = get_db_connection()
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
        conn.commit()
    except Exception as exc:
        logger.error(f"Error writing setting {key}: {exc}")
    finally:
        if conn:
            conn.close()


def get_scan_window_days():
    """Return the configured scan lookback window in days."""
    value = _get_setting_value('scan_window_days', DEFAULT_SCAN_WINDOW_DAYS)
    try:
        days = int(value)
        return days if days > 0 else DEFAULT_SCAN_WINDOW_DAYS
    except (TypeError, ValueError):
        return DEFAULT_SCAN_WINDOW_DAYS


def _window_label_to_days(label):
    """Map UI-friendly labels to integer day windows."""
    if not label:
        return None
    return WINDOW_PRESET_MAP.get(label.lower())


def _days_to_window_label(days):
    """Convert stored day values into the UI label."""
    try:
        return 'daily' if int(days) <= 1 else 'weekly'
    except (TypeError, ValueError):
        return 'weekly'


def record_scan_log(email_data, outcome, reason=None, metadata=None, company=None, role=None, status=None):
    """Persist a single scan decision for later inspection."""
    conn = None
    try:
        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO scan_logs
                (email_id, subject, sender, company, role, status_value, outcome, reason, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                email_data.get('id'),
                email_data.get('subject'),
                email_data.get('sender'),
                company,
                role,
                status,
                outcome,
                reason,
                json.dumps(metadata or {}),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )
        )
        conn.commit()
    except Exception as exc:
        logger.error(f"Failed to record scan log: {exc}")
    finally:
        if conn:
            conn.close()

# Function to load credentials
def load_credentials():
    """Loads credentials from token.pickle."""
    creds = None
    token_path = 'token.pickle'
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)
    return creds

# Initialize Agents (moved to after OAuth flow)
classifier_agent = ClassifierAgent()
database_agent = DatabaseAgent()
notification_agent = NotificationAgent(
    smtp_server=smtp_server,
    smtp_port=smtp_port,
    username=email_username,
    password=email_password
)

SKIP_EMAIL_DUMPS = os.getenv('SKIP_EMAIL_DUMPS', '').lower() in ('1', 'true', 'yes')

## DB helpers now imported from utils.db_utils

@app.route('/')
def index():
    conn = None
    try:
        # Check if credentials exist and are valid
        token_path = 'token.pickle'
        is_authenticated = False
        
        if os.path.exists(token_path):
            try:
                with open(token_path, 'rb') as token:
                    creds = pickle.load(token)
                is_authenticated = creds and creds.valid
                
                # Force token refresh if it exists but auth fails
                if not is_authenticated and hasattr(creds, 'refresh_token'):
                    try:
                        creds.refresh(Request())
                        with open(token_path, 'wb') as token:
                            pickle.dump(creds, token)
                        is_authenticated = True
                    except Exception as refresh_error:
                        logger.error(f"Error refreshing token: {str(refresh_error)}")
            except Exception as e:
                logger.error(f"Error checking credentials: {str(e)}")
        
        if not is_authenticated:
            # We'll still show the page but with "disconnected" status
            pass
        
        # Get monitored email and last scan time
        conn = get_db_connection()
        cursor = conn.execute("SELECT value FROM settings WHERE key = 'monitored_email'")
        row = cursor.fetchone()
        monitored_email = row['value'] if row else 'elyamworks@gmail.com'
        
        cursor = conn.execute("SELECT value FROM settings WHERE key = 'last_scan_time'")
        row = cursor.fetchone()
        last_scan_time = row['value'] if row else None

        cursor = conn.execute("SELECT value FROM settings WHERE key = 'scan_window_days'")
        row = cursor.fetchone()
        try:
            scan_window_days = int(row['value']) if row else DEFAULT_SCAN_WINDOW_DAYS
        except (TypeError, ValueError):
            scan_window_days = DEFAULT_SCAN_WINDOW_DAYS
        scan_window = _days_to_window_label(scan_window_days)
        
        # Get applications
        applications = conn.execute('SELECT * FROM applications ORDER BY id DESC').fetchall()

        status_counter = Counter()
        seven_days_ago = datetime.now() - timedelta(days=7)
        new_this_week = 0
        recent_updates = 0

        for app in applications:
            status_counter[app['status']] += 1
            applied_date = _safe_parse_date(app['date_applied'])
            status_date_value = _safe_parse_date(app['status_date'])

            if applied_date and applied_date >= seven_days_ago:
                new_this_week += 1
            if status_date_value and status_date_value >= seven_days_ago:
                recent_updates += 1

        summary = {
            'total': len(applications),
            'new_this_week': new_this_week,
            'recent_updates': recent_updates,
            'offers': status_counter.get('Offer', 0)
        }
        
        return render_template('dashboard.html', 
                              applications=applications,
                              is_authenticated=is_authenticated,
                              monitored_email=monitored_email,
                              last_scan_time=last_scan_time,
                              scan_window=scan_window,
                              summary=summary,
                              status_counter=status_counter)
    except Exception as e:
        logger.error(f"Error loading index: {str(e)}")
        return jsonify({'error': 'Failed to load applications'}), 500
    finally:
        if conn:
            conn.close()


@app.route('/guide')
def guide():
    """Render the in-app user manual page."""
    conn = None
    try:
        token_path = 'token.pickle'
        is_authenticated = False

        if os.path.exists(token_path):
            try:
                with open(token_path, 'rb') as token:
                    creds = pickle.load(token)
                is_authenticated = creds and creds.valid

                if not is_authenticated and hasattr(creds, 'refresh_token'):
                    try:
                        creds.refresh(Request())
                        with open(token_path, 'wb') as token:
                            pickle.dump(creds, token)
                        is_authenticated = True
                    except Exception as refresh_error:
                        logger.error(f"Error refreshing token for guide page: {str(refresh_error)}")
            except Exception as cred_error:
                logger.error(f"Error checking credentials for guide page: {str(cred_error)}")

        conn = get_db_connection()
        cursor = conn.execute("SELECT value FROM settings WHERE key = 'monitored_email'")
        row = cursor.fetchone()
        guide_monitored_email = row['value'] if row else monitored_email

        cursor = conn.execute("SELECT value FROM settings WHERE key = 'last_scan_time'")
        row = cursor.fetchone()
        last_scan_time = row['value'] if row else None

        return render_template(
            'new_guide.html',
            is_authenticated=is_authenticated,
            monitored_email=guide_monitored_email,
            last_scan_time=last_scan_time
        )
    except Exception as exc:
        logger.error(f"Error loading guide page: {str(exc)}")
        return render_template('error.html', error='Failed to load user guide'), 500
    finally:
        if conn:
            conn.close()

@app.route('/start_auth')
def start_auth():
    """Start the OAuth flow by redirecting to Google's auth page"""
    try:
        # Generate a secure random state
        state = secrets.token_urlsafe(16)
        # Store state in session with consistent key
        session['state'] = state
        # Make session permanent so it doesn't expire
        session.permanent = True
        
        logger.debug(f"Generated and stored state in session: {state}")
        
        # Create flow with desktop app credentials (less restrictions)
        flow = InstalledAppFlow.from_client_config(
            client_config={
                "installed": {  # Change from "web" to "installed"
                    "client_id": google_client_id,
                    "client_secret": google_client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "redirect_uris": [google_redirect_uri]
                }
            },
            scopes=["https://www.googleapis.com/auth/gmail.readonly"],
            redirect_uri=google_redirect_uri
        )

        # Generate authorization URL with state parameter
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            state=state,
            prompt='consent'
        )

        logger.debug(f"Redirecting to auth URL: {auth_url}")
        return redirect(auth_url)
    except Exception as e:
        logger.error(f"Error starting auth flow: {str(e)}")
        return render_template('error.html', error=str(e))

@app.route('/initialize_agents')
def initialize_agents():
    try:
        global gmail_service, email_monitor_agent
        gmail_service = get_gmail_service()
        email_monitor_agent = EmailMonitorAgent(gmail_service=gmail_service)
        return jsonify({'success': 'Agents initialized successfully'})
    except Exception as e:
        logger.error(f"Error initializing agents: {str(e)}")
        return jsonify({'error': 'Failed to initialize agents'}), 500

@app.route('/oauth2callback')
def oauth2callback():
    """Handle the OAuth 2.0 server callback."""
    try:
        # Log all request parameters for debugging
        logger.debug(f"Callback received with args: {request.args}")
        logger.debug(f"Full URL: {request.url}")
        
        # Check for error parameter from Google
        if 'error' in request.args:
            error = request.args.get('error')
            logger.error(f"OAuth error returned from Google: {error}")
            return render_template('error.html', 
                                  error=f"Authentication error: {error}",
                                  message="Please try authenticating again.")
        
        # Get authorization code
        code = request.args.get('code')
        if not code:
            logger.error("No authorization code in request args")
            return render_template('error.html', 
                                  error="No authorization code received",
                                  message="Please try authenticating again.")
        
        # Get state (with more flexibility)
        stored_state = session.get('state')
        received_state = request.args.get('state')
        
        logger.debug(f"Stored state in session: {stored_state}")
        logger.debug(f"Received state from request: {received_state}")
        
        # Create flow with desktop app configuration
        flow = InstalledAppFlow.from_client_config(
            {
                "installed": {
                    "client_id": google_client_id,
                    "client_secret": google_client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "redirect_uris": ["http://localhost:8080/oauth2callback"]
                }
            },
            scopes=["https://www.googleapis.com/auth/gmail.readonly"],
            redirect_uri="http://localhost:8080/oauth2callback"
        )

        try:
            # Exchange code for token
            flow.fetch_token(
                code=code,  # Explicitly pass the code parameter
                # Don't include the full URL to avoid redirect_uri issues
                # authorization_response=request.url,
                # State is optional
                state=received_state if stored_state == received_state else None
            )
            
            # Store credentials
            creds = flow.credentials
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)

            logger.info("Successfully stored credentials")
            
            # Clear state from session
            if 'state' in session:
                session.pop('state', None)
                
            return redirect(url_for('index'))
            
        except Exception as fetch_error:
            logger.error(f"Token fetch error: {str(fetch_error)}")
            
            # For invalid_grant errors, start a new flow
            if "invalid_grant" in str(fetch_error).lower():
                logger.info("Invalid grant error - redirecting to start fresh auth flow")
                return redirect(url_for('clear_token'))
            
            return render_template('error.html', 
                                  error=f"Failed to obtain token: {str(fetch_error)}",
                                  message="This is often caused by an expired authorization code. Please try again.")

    except Exception as e:
        logger.error(f"OAuth callback error: {str(e)}")
        return render_template('error.html', 
                              error=str(e),
                              message="An unexpected error occurred during authentication.")

# Google OAuth setup
# Update the get_gmail_service function
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.modify']

def get_gmail_service():
    """Get authenticated Gmail service with proper error logging"""
    try:
        logger.info("Starting get_gmail_service function")
        creds = None
        token_path = 'token.pickle'
        credentials_path = 'credentials.json'
        
        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
                logger.info("Loaded credentials from token.pickle")
        else:
            logger.warning("No token.pickle file found")
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    logger.info("Refreshing expired credentials")
                    creds.refresh(Request())
                    logger.info("Credentials refreshed successfully")
                except Exception as e:
                    logger.error(f"Failed to refresh credentials: {str(e)}")
                    creds = None
            
            if not creds:
                if not os.path.exists(credentials_path):
                    logger.error(f"No credentials.json file found at {os.path.abspath(credentials_path)}")
                    return None
                
                logger.info("Starting new authentication flow")
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                creds = flow.run_local_server(port=8090)
                
                with open(token_path, 'wb') as token:
                    pickle.dump(creds, token)
                logger.info("New credentials saved to token.pickle")
        
        service = build('gmail', 'v1', credentials=creds)
        profile = service.users().getProfile(userId='me').execute()
        logger.info(f"Successfully authenticated as: {profile.get('emailAddress')}")
        
        email_address = profile.get('emailAddress')
        conn = get_db_connection()
        cursor = conn.execute("SELECT value FROM settings WHERE key = 'monitored_email'")
        row = cursor.fetchone()
        stored_email = row['value'] if row else None
        
        if not stored_email or stored_email.lower() != email_address.lower():
            logger.info(f"Updating monitored email from {stored_email} to {email_address}")
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", 
                        ('monitored_email', email_address))
            conn.commit()
        conn.close()
        
        return service
    except Exception as e:
        logger.error(f"Error in get_gmail_service: {str(e)}")
        logger.exception("Authentication error details:")
        return None

@app.route('/add', methods=['POST'])
@app.route('/add_application', methods=['POST'])
def add_application():
    try:
        data = request.get_json()
        logger.debug(f"Received data: {data}")
        
        # Required fields
        required_fields = ['company', 'role', 'job_type', 'country', 'date_applied', 'source']
        
        # Validate required fields
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Setting resume_version automatically to the same as role
        resume_version = data['role']
        
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO applications (
                company, role, job_type, country, source, date_applied, resume_version, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['company'],
            data['role'],
            data['job_type'],
            data['country'],
            data['source'],
            data['date_applied'],
            resume_version,
            'Pending'
        ))
        conn.commit()
        return jsonify({'success': 'Application added successfully'})
    
    except Exception as e:
        logger.error(f"Error adding application: {str(e)}")
        return jsonify({'error': 'Failed to add application'}), 500
    finally:
        conn.close()

@app.route('/delete', methods=['POST'])
@app.route('/delete_application', methods=['POST'])
def delete_application():
    try:
        data = request.get_json()
        logger.debug(f"Delete request data: {data}")
        
        if not data.get('company') or not data.get('role'):
            return jsonify({'error': 'Company and role are required'}), 400
        
        conn = get_db_connection()
        conn.execute('DELETE FROM applications WHERE company = ? AND role = ?',
                     (data['company'], data['role']))
        conn.commit()
        return jsonify({'success': 'Application deleted successfully'})
    
    except Exception as e:
        logger.error(f"Error deleting application: {str(e)}")
        return jsonify({'error': 'Failed to delete application'}), 500
    finally:
        conn.close()

@app.route('/export')
@app.route('/export_csv')
def export_to_csv():
    try:
        conn = get_db_connection()
        applications = conn.execute('SELECT * FROM applications ORDER BY id DESC').fetchall()
        
        csv_file = 'applications.csv'
        with open(csv_file, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([
                'Company', 'Role', 'Job Type', 'Country',
                'Source', 'Date Applied', 'Resume Version', 'Status'
            ])
            for app in applications:
                writer.writerow([
                    app['company'], app['role'], app['job_type'],
                    app['country'], app['source'], app['date_applied'],
                    app['resume_version'], app['status']
                ])
        
        return send_file(
            csv_file,
            as_attachment=True,
            download_name='job_applications.csv',
            mimetype='text/csv'
        )
    
    except Exception as e:
        logger.error(f"Error exporting to CSV: {str(e)}")
        return jsonify({'error': 'Failed to export applications'}), 500
    finally:
        conn.close()

@app.route('/update_status', methods=['POST'])
def update_status():
    try:
        data = request.get_json()
        logger.debug(f"Status update request data: {data}")
        
        if not all(key in data for key in ['company', 'role', 'status']):
            return jsonify({'error': 'Missing required fields'}), 400
        
        valid_statuses = ['Pending', 'Rejected', 'Interview', 'Assignment', 'Offer']
        if data['status'] not in valid_statuses:
            return jsonify({'error': 'Invalid status value'}), 400
        
        # Get current date for status update
        today = datetime.now().strftime('%Y-%m-%d')
        
        conn = get_db_connection()
        cursor = conn.execute('''
            UPDATE applications 
            SET status = ?, status_date = ?
            WHERE company = ? AND role = ?
        ''', (data['status'], today, data['company'], data['role']))
        
        if cursor.rowcount == 0:
            return jsonify({'error': 'Application not found'}), 404
        
        conn.commit()
        return jsonify({
            'success': 'Status updated successfully',
            'status_date': today
        })
    
    except Exception as e:
        logger.error(f"Error updating status: {str(e)}")
        return jsonify({'error': 'Failed to update status'}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@app.route('/edit', methods=['POST'])
@app.route('/edit_application', methods=['POST'])
def edit_application():
    try:
        data = request.get_json()
        logger.debug(f"Edit request data: {data}")
        
        required_fields = ['original_company', 'original_role', 'company', 'role', 
                         'job_type', 'country', 'date_applied', 'source']
        if not all(key in data for key in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400
        
        conn = get_db_connection()
        cursor = conn.execute('''
            UPDATE applications 
            SET company = ?, role = ?, job_type = ?, country = ?, 
                source = ?, date_applied = ?, resume_version = ?
            WHERE company = ? AND role = ?
        ''', (
            data['company'], data['role'], data['job_type'], 
            data['country'], data['source'], data['date_applied'],
            data['role'],  # Setting resume_version same as role
            data['original_company'], data['original_role']
        ))
        
        if cursor.rowcount == 0:
            return jsonify({'error': 'Application not found'}), 404
        
        conn.commit()
        return jsonify({'success': 'Application updated successfully'})
    
    except Exception as e:
        logger.error(f"Error updating application: {str(e)}")
        return jsonify({'error': 'Failed to update application'}), 500
    finally:
        if 'conn' in locals():
            conn.close()


@app.route('/filter_applications', methods=['POST'])
def filter_applications():
    """Filter applications by various criteria"""
    try:
        data = request.get_json()
        logger.debug(f"Filter request data: {data}")

        query = "SELECT * FROM applications WHERE 1=1"
        params = []

        if data.get('status'):
            query += " AND status = ?"
            params.append(data['status'])

        if data.get('date_from'):
            query += " AND status_date >= ?"
            params.append(data['date_from'])

        if data.get('date_to'):
            query += " AND status_date <= ?"
            params.append(data['date_to'])

        if data.get('applied_from'):
            query += " AND date_applied >= ?"
            params.append(data['applied_from'])

        if data.get('applied_to'):
            query += " AND date_applied <= ?"
            params.append(data['applied_to'])

        if data.get('new_only'):
            seven_days_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            query += " AND date_applied >= ?"
            params.append(seven_days_ago)

        if data.get('recently_updated'):
            seven_days_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            query += " AND status_date >= ?"
            params.append(seven_days_ago)

        sort_field = data.get('sort_by', 'id')
        sort_dir = data.get('sort_dir', 'DESC')
        allowed_fields = ['id', 'company', 'role', 'status', 'date_applied', 'status_date']
        allowed_dirs = ['ASC', 'DESC']

        if sort_field in allowed_fields and sort_dir in allowed_dirs:
            query += f" ORDER BY {sort_field} {sort_dir}"
        else:
            query += " ORDER BY id DESC"

        conn = get_db_connection()
        cursor = conn.execute(query, params)
        applications = cursor.fetchall()

        result = [dict(app) for app in applications]

        return jsonify({
            'success': True,
            'filtered_count': len(result),
            'applications': result
        })

    except Exception as e:
        logger.error(f"Error filtering applications: {str(e)}")
        return jsonify({'error': 'Failed to filter applications'}), 500
    finally:
        if 'conn' in locals() and conn:
            conn.close()


@app.route('/get_application')
def get_application():
    """Get application details for editing"""
    try:
        company = request.args.get('company')
        role = request.args.get('role')

        if not company or not role:
            return jsonify({'error': 'Company and role are required'}), 400

        conn = get_db_connection()
        cursor = conn.execute(
            "SELECT * FROM applications WHERE company = ? AND role = ?",
            (company, role)
        )
        application = cursor.fetchone()

        if not application:
            return jsonify({'error': 'Application not found'}), 404

        app_dict = dict(application)

        return jsonify({
            'success': True,
            'application': app_dict
        })

    except Exception as e:
        logger.error(f"Error getting application: {str(e)}")
        return jsonify({'error': 'Failed to get application'}), 500
    finally:
        if 'conn' in locals() and conn:
            conn.close()

# Function to scan emails and update applications
def scan_and_update_applications(target_email=None):
    """Scan emails using the unified processing pipeline."""
    try:
        logger.info("Starting scan_and_update_applications function")

        # Determine which email to scan
        if not target_email:
            target_email = _get_setting_value('monitored_email', monitored_email)

        if not target_email:
            logger.warning("No monitored email configured; aborting scan")
            return 0

        lookback_days = get_scan_window_days()
        logger.info(f"Scanning emails for {target_email} with {lookback_days}-day window")

        result = scan_emails_and_process(target_email, lookback_days=lookback_days)
        logger.info(f"Scheduled scan result: {result}")
        return result
    except Exception as e:
        logger.error(f"Error scanning and updating applications: {str(e)}")
        logger.exception("Scheduled scan failure")
        return 0

# Function to send summary email
def send_summary_email():
    conn = None
    try:
        conn = get_db_connection()
        applications = conn.execute('SELECT * FROM applications WHERE date_applied >= ?', 
                                    (datetime.now() - timedelta(days=1),)).fetchall()
        summary = "Summary of new applications:\n\n"
        for app in applications:
            summary += f"Company: {app['company']}, Role: {app['role']}, Status: {app['status']}\n"
        
        # Use ChatGPT to summarize the updates
        openai.api_key = openai_api_key
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes job application updates."},
                {"role": "user", "content": f"Summarize the following updates:\n{summary}"}
            ],
            max_tokens=150
        )
        summary = response.choices[0].message["content"].strip()
        
        # Send the summary email
        notification_agent.send_email(
            to_address='elyamworks@gmail.com',
            subject="Daily Summary of Job Applications",
            body=summary
        )
    except Exception as e:
        logger.error(f"Error sending summary email: {str(e)}")
    finally:
        if conn:
            conn.close()

# Initialize scheduler in a function that can be conditionally called
def init_scheduler():
    scheduler = BackgroundScheduler()
    
    # Add jobs to scheduler
    scheduler.add_job(scan_and_update_applications, 'interval', hours=1)
    scheduler.add_job(send_summary_email, 'cron', hour=10, minute=0)
    
    # Start the scheduler
    scheduler.start()
    
    # Register shutdown handler
    atexit.register(lambda: scheduler.shutdown())
    
    return scheduler

@app.route('/clear_token')
def clear_token():
    """Clear the token file and redirect to auth status"""
    token_path = 'token.pickle'
    if os.path.exists(token_path):
        os.remove(token_path)
        logger.info("Token file removed")
    
    # Also clear any session data
    session.clear()
    
    return redirect(url_for('auth_status'))

@app.route('/auth_status')
def auth_status():
    """Show authentication status and debugging information"""
    token_path = 'token.pickle'
    has_token = os.path.exists(token_path)
    
    if has_token:
        try:
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
            creds_valid = creds and creds.valid
        except Exception as e:
            logger.error(f"Error loading credentials: {str(e)}")
            creds_valid = False
    else:
        creds_valid = False
    
    auth_info = {
        'has_token_file': has_token,
        'credentials_valid': creds_valid,
        'session_contains_state': 'state' in session,
        'session_keys': list(session.keys()) if session else [],
        'redirect_uri': google_redirect_uri
    }
    
    # Return HTML template instead of JSON
    return render_template('auth_status.html', auth_info=auth_info)

# Add these new routes
@app.route('/settings', methods=['GET'])
def settings_page():
    """Display settings page with integrated auth status"""
    try:
        # Get the monitored email
        conn = get_db_connection()
        cursor = conn.execute("SELECT value FROM settings WHERE key = 'monitored_email'")
        row = cursor.fetchone()
        email = row['value'] if row else monitored_email
        
        # Check authentication status
        token_path = 'token.pickle'
        has_token_file = os.path.exists(token_path)
        credentials_valid = False
        is_authenticated = False
        
        if has_token_file:
            try:
                # FIXED: Don't use from_authorized_user - directly load with pickle instead
                with open(token_path, 'rb') as token:
                    creds = pickle.load(token)
                    credentials_valid = creds and creds.valid
                    is_authenticated = credentials_valid
            except Exception as e:
                logger.error(f"Error loading credentials: {str(e)}")
        
        return render_template(
            'settings.html', 
            email=email,
            monitored_email=email,
            has_token_file=has_token_file,
            credentials_valid=credentials_valid,
            is_authenticated=is_authenticated
        )
    except Exception as e:
        logger.error(f"Error loading settings: {str(e)}")
        return jsonify({'error': 'Failed to load settings'}), 500
    finally:
        if 'conn' in locals() and conn:
            conn.close()

@app.route('/settings/email', methods=['POST'])
def update_email():
    """Update monitored email"""
    try:
        data = request.get_json()
        new_email = data.get('email')
        
        if not new_email or '@' not in new_email:
            return jsonify({'error': 'Invalid email format'}), 400
            
        conn = get_db_connection()
        conn.execute("""
            INSERT OR REPLACE INTO settings (key, value) 
            VALUES ('monitored_email', ?)
        """, (new_email,))
        conn.commit()
        
        return jsonify({'success': True, 'message': 'Email updated successfully'})
    except Exception as e:
        logger.error(f"Error updating email: {str(e)}")
        return jsonify({'error': 'Failed to update email'}), 500
    finally:
        if 'conn' in locals():
            conn.close()


@app.route('/settings/scan_window', methods=['POST'])
def update_scan_window():
    """Persist the preferred scan lookback window."""
    global scan_status
    try:
        data = request.get_json(force=True)
        window = data.get('window', '').lower()

        if window not in WINDOW_PRESET_MAP:
            return jsonify({'error': 'Invalid window option'}), 400

        days = WINDOW_PRESET_MAP[window]
        _set_setting_value('scan_window_days', days)
        scan_status['window_days'] = days

        return jsonify({'success': True, 'window': window, 'days': days})
    except Exception as e:
        logger.error(f"Error updating scan window: {str(e)}")
        return jsonify({'error': 'Failed to update scan window'}), 500

@app.route('/scan_now')
def scan_now():
    """Manually trigger email scanning"""
    global scan_status  # Move global declaration to the top of the function
    
    try:
        requested_window = request.args.get('window', '').lower()
        requested_days = request.args.get('lookback_days')
        lookback_days = None

        if requested_days:
            try:
                lookback_days = max(1, int(requested_days))
            except ValueError:
                lookback_days = None

        if lookback_days is None:
            lookback_days = _window_label_to_days(requested_window) or get_scan_window_days()

        # Check authentication
        token_path = 'token.pickle'
        if not os.path.exists(token_path):
            return jsonify({'error': 'Not authenticated with Gmail'}), 401
            
        # Get the monitored email
        conn = get_db_connection()
        cursor = conn.execute("SELECT value FROM settings WHERE key = 'monitored_email'")
        row = cursor.fetchone()
        target_email = row['value'] if row else monitored_email
        
        # Update last scan time
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("""
            INSERT OR REPLACE INTO settings (key, value) 
            VALUES ('last_scan_time', ?)
        """, (now,))
        conn.commit()
        conn.close()
        
        # Create Gmail service 
        service = get_gmail_service()
        if not service:
            return jsonify({'error': 'Failed to initialize Gmail service'}), 500
        
        # Update scan status
        scan_status = {
            'is_scanning': True,
            'start_time': now,
            'end_time': None,
            'status': 'scanning',
            'result': None,
            'error': None,
            'window_days': lookback_days,
            'updates': []
        }
        
        # Run scan in a background thread with timeout protection
        def run_scan():
            global scan_status  # Need global here too
            try:
                # Use a direct sync function instead of asyncio for more reliable behavior
                result = scan_emails_and_process(target_email, service, lookback_days=lookback_days)
                
                # Update status with result
                scan_status['end_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                scan_status['status'] = 'completed'
                scan_status['result'] = result
                scan_status['is_scanning'] = False
                
                logger.info(f"Scan completed with result: {result}")
            except Exception as e:
                scan_status['status'] = 'error'
                scan_status['error'] = str(e)
                scan_status['is_scanning'] = False
                scan_status['end_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                logger.error(f"Error in run_scan: {str(e)}")
                logger.exception("Stack trace:")
        
        # Start the background thread with a timeout
        thread = threading.Thread(target=run_scan)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True, 
            'message': f'Scanning emails for {target_email}',
            'last_scan_time': now,
            'window_days': lookback_days
        })
    except Exception as e:
        logger.error(f"Error triggering scan: {str(e)}")
        logger.exception("Stack trace:")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/scan_status')
def get_scan_status():
    """Get the current status of the email scan"""
    try:
        # Also get the last scan time from the database
        conn = get_db_connection()
        cursor = conn.execute("SELECT value FROM settings WHERE key = 'last_scan_time'")
        row = cursor.fetchone()
        last_scan_time = row['value'] if row else None
        conn.close()
        
        # Return the current scan status plus the last scan time
        return jsonify({
            'is_scanning': scan_status['is_scanning'],
            'status': scan_status['status'],
            'start_time': scan_status['start_time'],
            'end_time': scan_status['end_time'],
            'result': scan_status['result'],
            'error': scan_status['error'],
            'last_scan_time': last_scan_time,
            'window_days': scan_status.get('window_days', get_scan_window_days()),
            'updates': scan_status.get('updates', [])
        })
    except Exception as e:
        logger.error(f"Error getting scan status: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/scan_logs')
def scan_logs_endpoint():
    """Return the latest scan log entries for UI inspection."""
    conn = None
    try:
        limit_arg = request.args.get('limit', 15)
        try:
            limit = int(limit_arg)
        except (TypeError, ValueError):
            limit = 15
        limit = max(1, min(limit, MAX_SCAN_LOG_RETURN))

        conn = get_db_connection()
        rows = conn.execute(
            """
            SELECT email_id, subject, sender, company, role, status_value, outcome, reason, metadata, created_at
            FROM scan_logs
            ORDER BY datetime(created_at) DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()

        logs = []
        for row in rows:
            metadata = {}
            if row['metadata']:
                try:
                    metadata = json.loads(row['metadata'])
                except json.JSONDecodeError:
                    metadata = {}
            logs.append({
                'email_id': row['email_id'],
                'subject': row['subject'],
                'sender': row['sender'],
                'company': row['company'],
                'role': row['role'],
                'status': row['status_value'],
                'outcome': row['outcome'],
                'reason': row['reason'],
                'metadata': metadata,
                'created_at': row['created_at']
            })

        return jsonify({'logs': logs, 'limit': limit})
    except Exception as e:
        logger.error(f"Error fetching scan logs: {str(e)}")
        return jsonify({'error': 'Failed to load scan logs'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/authenticate')
def authenticate():
    """Force a new authentication flow"""
    try:
        # Remove existing token if it exists
        token_path = 'token.pickle'
        if os.path.exists(token_path):
            os.remove(token_path)
            logger.info("Removed existing token.pickle")
        
        # Get fresh authentication
        service = get_gmail_service()
        if service:
            # Get authenticated user email
            profile = service.users().getProfile(userId='me').execute()
            email = profile.get('emailAddress')
            return jsonify({
                'success': True,
                'message': f'Successfully authenticated as {email}',
                'email': email
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Authentication failed. Check logs for details.'
            }), 401
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        logger.exception("Stack trace:")
        return jsonify({
            'success': False,
            'message': f'Authentication error: {str(e)}'
        }), 500

def dump_email_for_debugging(email_data, folder="email_dumps"):
    """Save email content to file for debugging purposes"""
    try:
        # Create dump folder if it doesn't exist
        if not os.path.exists(folder):
            os.makedirs(folder)
        
        # Generate filename based on subject and date
        safe_subject = re.sub(r'[^\w\-_]', '_', email_data['subject'])[:50]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{folder}/{timestamp}_{safe_subject}.txt"
        
        # Write email content to file
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"SUBJECT: {email_data['subject']}\n")
            f.write(f"FROM: {email_data['sender']}\n")
            f.write(f"DATE: {email_data['date']}\n")
            f.write(f"ID: {email_data['id']}\n")
            f.write("\n---- BODY ----\n\n")
            f.write(email_data['body'])
        
        logger.info(f"Dumped email content to {filename}")
    except Exception as e:
        logger.error(f"Error dumping email: {str(e)}")

def get_application_details_with_ai(email_data):
    """Use OpenAI to extract application details from email"""
    try:
        # Skip if OpenAI API key is not set
        if not openai_api_key:
            logger.warning("OpenAI API key not set, skipping AI extraction")
            return None
            
        # Limit text to avoid token limits
        max_chars = 4000
        truncated_text = email_data['body'][:max_chars]
        
        # Create prompt with email content
        prompt = f"""
Extract job application information from this email.
Subject: {email_data['subject']}
Sender: {email_data['sender']}
Body excerpt:
{truncated_text}

Return ONLY a JSON object with these fields:
1. company: The company name (required)
2. role: The job title/role (required)
3. status: One of [Pending, Rejected, Interview, Assignment, Offer]
4. is_job_related: true/false - is this a job application email?

If you can't determine the company or role, or if this isn't a job-related email, set is_job_related to false.
        """
        
        # Call OpenAI API
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You extract job application details from emails."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,  # Low temperature for more consistent results
            max_tokens=300
        )
        
        # Parse JSON response
        result_text = response.choices[0].message["content"].strip()
        try:
            # Try to parse as JSON
            result = json.loads(result_text)
            
            # Validate required fields
            if result.get('is_job_related', False) and result.get('company') and result.get('role'):
                logger.info(f"AI extracted: {result}")
                return result
            else:
                logger.info(f"AI determined email is not job-related or missing info: {result}")
                return None
        except json.JSONDecodeError:
            logger.error(f"Failed to parse AI response as JSON: {result_text}")
            return None
            
    except Exception as e:
        logger.error(f"Error using AI to extract application details: {str(e)}")
        return None

def determine_email_status(email_data):
    """Determine application status from email with improved accuracy"""
    subject = email_data.get('subject', '').lower()
    body = email_data.get('body', '').lower()
    combined_text = subject + ' ' + body
    
    # Define strong indicator patterns for each status 
    status_patterns = {
        'Rejected': [
            r'\b(?:unfortunately|regret|regrettably|not\s+(?:moving|proceeding))\b',
            r'\b(?:not\s+(?:selected|chosen|considered|pursue|proceed|move|shortlisted))\b',
            r'\b(?:other\s+candidates|pursuing\s+other|different\s+direction)\b',
            r'\b(?:suitable\s+match|not\s+suitable|not\s+a\s+fit|position\s+has\s+been\s+filled)\b',
            r'\b(?:your\s+application\s+was\s+not|we\s+will\s+not\s+be)\b',
            r'\bunsuccessful\b',
            r'\breceived\s+a\s+large\s+number\s+of\s+applications\b',
            r'\bcannot\s+proceed\s+with\s+your\s+application\b',
            r'\bthank\s+you\s+for\s+your\s+interest\b.*\bbest\s+wishes\b',  # Common rejection phrase combo 
        ],
        'Interview': [
            r'\b(?:interview|schedule\s+a\s+(?:call|meeting)|like\s+to\s+speak|speak\s+with\s+you)\b',
            r'\b(?:next\s+(?:step|stage)|move\s+forward|further\s+discuss|conversation)\b',
            r'\b(?:availability|available\s+for|when\s+(?:are|would)\s+you\s+be)\b.*\b(?:interview|call|meet)\b',
            r'\b(?:set\s+up\s+a|schedule\s+a|arranging\s+a)\b.*\b(?:interview|call|meeting)\b',
            r'\b(?:invite\s+you\s+to|would\s+like\s+to\s+invite)\b',
            r'\b(?:recruiter|hiring\s+manager|team)\s+would\s+like\s+to\b',
            r'\bnext\s+round\b',
            r'\bcall\s+details\b',
            r'\bmeeting\s+invite\b',
            r'\binterview\s+confirmation\b',
        ],
        'Assignment': [
            r'\b(?:assignment|test|challenge|coding\s+(?:challenge|exercise|task)|take-home)\b',
            r'\b(?:technical\s+(?:assessment|task|exercise|challenge)|skills\s+assessment)\b',
            r'\b(?:complete\s+(?:the\s+following|this\s+assignment)|submit\s+(?:a|your))\b',
            r'\b(?:assessment\s+(?:link|details|instructions)|instructions\s+for\s+the\s+assessment)\b',
            r'\b(?:please\s+(?:complete|solve|implement|code))\b',
            r'\b(?:deadline|due\s+(?:date|by|in))\b.*\b(?:assignment|test|challenge|task)\b',
            r'\bproject\s+(?:brief|details|instructions)\b',
            r'\btechnical\s+evaluation\b',
        ],
        'Offer': [
            r'\b(?:job\s+offer|offer\s+(?:letter|details|package)|employment\s+offer)\b',
            r'\b(?:pleased\s+to\s+offer|happy\s+to\s+offer|formal\s+offer|extend\s+an\s+offer)\b',
            r'\b(?:starting\s+(?:date|salary)|compensation\s+package|benefits\s+package)\b',
            r'\b(?:accept\s+(?:this|the|our)\s+offer|offer\s+acceptance|offer\s+of\s+employment)\b',
            r'\b(?:welcome\s+(?:to\s+the\s+team|aboard|onboard)|onboarding\s+process)\b',
            r'\b(?:employment\s+agreement|contract\s+(?:attached|enclosed))\b',
            r'\bcongratulations\b.*\b(?:position|role|joining|selected)\b',
            r'\bwe\s+are\s+(?:pleased|delighted|happy|thrilled)\s+to\b.*\b(?:inform|tell|let\s+you\s+know|advise)\b',
        ]
    }
    
    # Check for strong status indicators
    for status, patterns in status_patterns.items():
        for pattern in patterns:
            if re.search(pattern, combined_text):
                logger.info(f"Found status pattern for {status}: {pattern}")
                return status
    
    # Fallback to checking for confirmation words if no strong indicators found
    confirmation_patterns = [
        r'\b(?:received|confirm|thank\s+you\s+for|application\s+(?:received|submitted|complete))\b',
        r'\b(?:we\s+have\s+received|has\s+been\s+received|successfully\s+(?:submitted|received))\b',
        r'\b(?:in\s+review|being\s+reviewed|under\s+(?:consideration|review))\b',
        r'\b(?:acknowledge|acknowledging|receipt\s+of)\b',
        r'\b(?:thank\s+you\s+for\s+applying|thanks\s+for\s+your\s+application)\b'
    ]
    
    for pattern in confirmation_patterns:
        if re.search(pattern, combined_text):
            logger.info(f"Found confirmation pattern: {pattern}")
            return "Pending"
    
    # If all else fails, default to Pending
    logger.info("No status patterns found, defaulting to Pending")
    return "Pending"


def infer_job_type(email_data, company_name=None):
    """Infer job type (Remote/Hybrid/On-site) using keyword heuristics and overrides."""
    if company_name and company_name.lower() in JOB_TYPE_OVERRIDES:
        return JOB_TYPE_OVERRIDES[company_name.lower()]

    text = f"{email_data.get('subject', '')} {email_data.get('body', '')}".lower()
    hybrid_terms = ['hybrid', 'onsite/remote', 'on-site/remote', 'mix of remote', 'split schedule', 'partly remote']
    remote_terms = ['remote', 'work from home', 'wfh', 'fully remote', 'distributed team']
    onsite_terms = ['on-site', 'onsite', 'in office', 'in-office', 'office-based', 'on site']

    def _contains_any(terms):
        return any(term in text for term in terms)

    if _contains_any(hybrid_terms):
        return 'Hybrid'
    if _contains_any(remote_terms):
        return 'Remote'
    if _contains_any(onsite_terms):
        return 'On-site'

    return 'Remote'


def _safe_parse_date(value):
    """Parse YYYY-MM-DD strings without raising."""
    if not value:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%d')
    except Exception:
        return None

def classify_email_content(email_data, monitored_email):
    """Determine if email contains job application info while exposing debug metadata."""
    debug_info = {
        'reason': None,
        'signal': None,
        'pattern': None,
        'company_candidate': None
    }
    try:
        if not SKIP_EMAIL_DUMPS:
            dump_email_for_debugging(email_data)
        
        raw_subject = email_data.get('subject', '')
        raw_body = email_data.get('body', '')
        normalized_subject = raw_subject.lower()
        normalized_body = raw_body.lower()
        combined_text = normalized_subject + ' ' + normalized_body
        
        strict_patterns = [
            r'thank\s+you\s+for\s+(?:your|submitting|completing)\s+(?:application|applying)',
            r'(?:your|the)\s+application\s+(?:has\s+been|was)\s+(?:received|submitted|confirmed)',
            r'we\s+(?:have|\'ve)\s+received\s+your\s+application',
            r'application\s+(?:confirmation|received|submitted|complete)',
            r'confirmation\s+of\s+your\s+(?:job|position|role)\s+application',
            r'we\s+are\s+currently\s+reviewing\s+your\s+application',
            r'your\s+interest\s+in\s+(?:the|this|our)\s+(?:position|role|job|opportunity)',
            r'in\s+response\s+to\s+your\s+(?:recent|job)\s+application',
            r'thank\s+you\s+for\s+expressing\s+interest\s+in\s+(?:the|this|our)\s+(?:position|role|vacancy)'
        ]

        fallback_patterns = [
            r'your\s+application\s+(?:to|for)',
            r'we\s+noticed\s+your\s+application',
            r'has\s+received\s+your\s+application',
            r'we\s+are\s+reviewing\s+your\s+application',
            r'update\s+on\s+your\s+application',
            r'consideration\s+for\s+the\s+position',
            r'next\s+steps\s+in\s+the\s+process',
            r'invitation\s+to\s+(?:a\s+)?(?:phone|video)?\s*interview',
            r'spark\s+hire',
            r'phone\s+interview',
            r'let\'s\s+have\s+a\s+chat'
        ]

        matching_pattern = next((pattern for pattern in strict_patterns if re.search(pattern, combined_text, re.IGNORECASE)), None)
        signal_strength = 'strict'

        if not matching_pattern:
            matching_pattern = next((pattern for pattern in fallback_patterns if re.search(pattern, combined_text, re.IGNORECASE)), None)
            if matching_pattern:
                signal_strength = 'fallback'

        if not matching_pattern:
            primary_keywords = ['application', 'apply', 'applied', 'candidate', 'position', 'role', 'interview', 'offer']
            context_keywords = ['received', 'review', 'consideration', 'process', 'thank you', 'interest', 'invitation', 'schedule']
            keyword_hits = sum(1 for kw in primary_keywords if kw in combined_text)
            context_hits = sum(1 for kw in context_keywords if kw in combined_text)
            if keyword_hits >= 2 and context_hits >= 1:
                matching_pattern = 'keyword-signal'
                signal_strength = 'keywords'
            else:
                debug_info['reason'] = 'no_application_pattern'
                logger.info(f"Email does not match job application heuristics: {raw_subject}")
                return None, debug_info

        logger.info(f"Found job application confirmation pattern ({signal_strength}): {matching_pattern}")
        debug_info.update({'signal': signal_strength, 'pattern': matching_pattern})
        
        company_name = extract_company_name(email_data)
        debug_info['company_candidate'] = company_name
        if not company_name:
            debug_info['reason'] = 'company_not_found'
            logger.info(f"Could not extract company name from confirmed job application: {raw_subject}")
            return None, debug_info
            
        invalid_companies = ['linkedin', 'update', 'alert', 'notification', 'message', 
                           'tel aviv', 'new york', 'reminder', 'news']
        if any(inv.lower() in company_name.lower() for inv in invalid_companies):
            debug_info['reason'] = 'invalid_company_name'
            logger.info(f"Skipping invalid company name: {company_name}")
            return None, debug_info
            
        if len(company_name) < 3:
            debug_info['reason'] = 'company_name_short'
            logger.info(f"Company name too short: {company_name}")
            return None, debug_info
        
        role = extract_role(email_data) or "Position"
        status = determine_email_status(email_data)
        
        app_data = {
            'company': company_name,
            'role': role,
            'status': status,
            'email_id': email_data['id'],
            'email_date': email_data['date'],
            'job_type': infer_job_type(email_data, company_name),
            'country': 'Unknown',
            'source': 'Email',
            'date_applied': parse_date(email_data['date'])
        }
        
        debug_info['reason'] = 'classified'
        logger.info(f"Classified email as {status} for {company_name}, role: {role}")
        return app_data, debug_info
        
    except Exception as e:
        debug_info['reason'] = 'exception'
        debug_info['error'] = str(e)
        logger.error(f"Error classifying email: {str(e)}")
        logger.exception("Classification error details:")
        return None, debug_info

def scan_emails_and_process(monitored_email, service=None, lookback_days=None):
    """Process emails and update application database"""
    try:
        logger.info(f"Starting email scan for {monitored_email}")
        
        # Initialize Gmail service if not provided
        if not service:
            service = get_gmail_service()
            
        if not service:
            logger.error("Failed to initialize Gmail service")
            return "failed: no service"
            
        # Search for relevant emails
        window_days = lookback_days or get_scan_window_days()
        emails = search_emails(service, monitored_email, days=window_days)
        logger.info(f"Found {len(emails)} potentially relevant emails")
        
        if not emails:
            logger.info("No relevant emails found to process")
            return "completed: no emails"
        
        # Process each email
        new_count = 0
        updated_count = 0
        errors = 0
        updated_applications = []
        
        for email in emails:
            try:
                # Extract full email content
                msg_data = get_email_content(service, email['id'])
                if not msg_data:
                    logger.debug(f"Could not get content for email {email['id']}")
                    record_scan_log({'id': email['id'], 'subject': None, 'sender': None}, 'error', 'missing_email_body', {'window_days': window_days})
                    continue
                    
                # Classify and extract application data
                app_data, debug_info = classify_email_content(msg_data, monitored_email)
                if not app_data:
                    record_scan_log(
                        msg_data,
                        'skipped',
                        debug_info.get('reason'),
                        {'classification': debug_info, 'window_days': window_days}
                    )
                    continue
                    
                # Update database with extracted info
                result = update_application_database(app_data)
                log_metadata = {
                    'classification': debug_info,
                    'db_result': result,
                    'window_days': window_days
                }
                if result['result'] == 'new':
                    new_count += 1
                    updated_applications.append({
                        'company': app_data['company'],
                        'role': app_data['role'],
                        'status': app_data['status'],
                        'date': result['date'],
                        'type': 'new'
                    })
                elif result['result'] == 'updated':
                    updated_count += 1
                    updated_applications.append({
                        'company': app_data['company'],
                        'role': app_data['role'],
                        'status': app_data['status'],
                        'date': result['date'],
                        'type': 'updated'
                    })
                elif result['result'] == 'error':
                    errors += 1

                record_scan_log(
                    msg_data,
                    result['result'],
                    result.get('message'),
                    log_metadata,
                    company=app_data['company'],
                    role=app_data['role'],
                    status=app_data['status']
                )
            except Exception as e:
                errors += 1
                logger.error(f"Error processing email {email['id']}: {str(e)}")
                logger.exception("Processing error details:")
                record_scan_log(
                    {'id': email['id'], 'subject': None, 'sender': None},
                    'error',
                    str(e),
                    {'window_days': window_days}
                )
        
        result_message = f"Email scan complete. Added {new_count} new applications, updated {updated_count} existing applications, {errors} errors"
        logger.info(result_message)
        
        # Store updated applications in scan_status for UI display
        global scan_status
        scan_status['updates'] = updated_applications
        scan_status['window_days'] = window_days
        
        return f"completed: {new_count} new, {updated_count} updated"
            
    except Exception as e:
        logger.error(f"Error in email scan process: {str(e)}")
        logger.exception("Stack trace:")
        return f"failed: {str(e)}"

def search_emails(service, email_address, days=30):
    """Search for job application related emails with STRICT criteria"""
    try:
        # Calculate date range for search
        today = datetime.now()
        start_date = (today - timedelta(days=days)).strftime('%Y/%m/%d')
        
        keyword_terms = [
            '"thank you for applying"',
            '"thank you for your application"',
            '"application received"',
            '"we received your application"',
            '"your application"',
            '"application review"',
            '"next steps"',
            '"job offer"',
            '"interview"',
            '"assignment"',
            'application',
            'applied',
            'candidate'
        ]
        keyword_query = ' OR '.join(keyword_terms)
        
        # Broader search query that still avoids noisy sources
        query = (
            f"(to:{email_address} OR cc:{email_address}) "
            f"after:{start_date} "
            f"({keyword_query}) "
            f"-from:linkedin -from:notifications@linkedin"
        )
        
        logger.info(f"Email search query: {query}")
        
        # Execute search
        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=200
        ).execute()
        
        messages = results.get('messages', [])
        logger.info(f"Found {len(messages)} emails in strict application search")
        return messages
    except Exception as e:
        logger.error(f"Error searching emails: {str(e)}")
        logger.exception("Search error details:")
        return []

def get_email_content(service, msg_id):
    """Retrieve and parse full email content"""
    try:
        # Get the email
        message = service.users().messages().get(
            userId='me', 
            id=msg_id, 
            format='full'
        ).execute()
        
        # Get headers
        headers = {header['name'].lower(): header['value'] for header in message['payload']['headers']}
        
        # Extract email details
        subject = headers.get('subject', '')
        sender = headers.get('from', '')
        date = headers.get('date', '')
        
        # Get body
        body = extract_email_body(message['payload'])
        
        return {
            'id': msg_id,
            'subject': subject,
            'sender': sender,
            'date': date,
            'body': body
        }
    except Exception as e:
        logger.error(f"Error retrieving email content for message {msg_id}: {str(e)}")
        return None

def extract_email_body(payload, body_text=""):
    """Recursively extract text from email with better MIME handling"""
    if 'body' in payload and 'data' in payload['body'] and payload['body']['data']:
        # Extract data directly from this part
        try:
            data = payload['body']['data']
            decoded = base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
            
            # If this is HTML content, strip tags
            if payload.get('mimeType') == 'text/html':
                decoded = re.sub(r'<[^>]+>', ' ', decoded)
                decoded = re.sub(r'\s+', ' ', decoded)  # Normalize whitespace
            
            body_text += decoded
        except Exception as e:
            logger.error(f"Error decoding email part: {str(e)}")
    
    # Process child parts recursively
    if 'parts' in payload:
        for part in payload['parts']:
            body_text = extract_email_body(part, body_text)
    
    return body_text

def update_application_database(app_data):
    """Add or update application in database with better validation"""
    conn = None
    try:
        # Validate application data
        if not app_data.get('company') or len(app_data['company']) < 3:
            logger.warning(f"Invalid company name: {app_data['company']}")
            return {'result': 'invalid', 'date': None, 'message': 'invalid_company'}
            
        # Skip common false positives
        skip_companies = [
            'update', 'alert', 'notification', 'reminder', 'message',
            'email', 'reply', 'response', 'list', 'news', 'newsletter'
        ]
        
        if app_data['company'].lower() in skip_companies:
            logger.warning(f"Skipping known false positive company: {app_data['company']}")
            return {'result': 'skipped', 'date': None, 'message': 'false_positive_company'}
        
        # Current date for status updates
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Case-insensitive matching
        conn = get_db_connection()
        cursor = conn.execute(
            "SELECT * FROM applications WHERE LOWER(company) = LOWER(?) AND LOWER(role) = LOWER(?)", 
            (app_data['company'], app_data['role'])
        )
        existing = cursor.fetchone()
        
        if existing:
            # Only update if the new status is different
            if existing['status'] != app_data['status']:
                conn.execute("""
                    UPDATE applications 
                    SET status = ?, status_date = ?
                    WHERE id = ?
                """, (
                    app_data['status'], 
                    today,
                    existing['id']
                ))
                conn.commit()
                logger.info(f"Updated application status: {app_data['company']} - {app_data['role']} from {existing['status']} to {app_data['status']}")
                return {'result': 'updated', 'date': today, 'message': 'status_updated'}
            else:
                logger.info(f"Application already exists with same status: {app_data['company']} - {app_data['role']} ({app_data['status']})")
                return {'result': 'existing', 'date': existing['status_date'], 'message': 'status_unchanged'}
        else:
            # Insert new application with today's date for status_date
            conn.execute("""
                INSERT INTO applications (
                    company, role, job_type, country, source, date_applied, 
                    resume_version, status, status_date
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                app_data['company'],
                standardize_role(app_data['role']),  # Use the standardized role
                app_data.get('job_type', 'Remote'),
                app_data.get('country', 'Unknown'),
                app_data.get('source', 'Email'),
                app_data['date_applied'],
                '1.0',  # Default resume version
                app_data['status'],
                today   # Use today for status_date
            ))
            conn.commit()
            logger.info(f"Added new application: {app_data['company']} - {app_data['role']} with status {app_data['status']}")
            return {'result': 'new', 'date': today, 'message': 'inserted'}
            
    except Exception as e:
        logger.error(f"Error updating application database: {str(e)}")
        logger.exception("Database update error details:")
        return {'result': 'error', 'date': None, 'message': str(e)}
    finally:
        if conn:
            conn.close()

def extract_company_name(email_data):
    """Extract company name from email data with strict filtering"""
    if not email_data.get('subject') or not email_data.get('sender'):
        logger.warning("Missing subject or sender in email data")
        return None
        
    subject = email_data['subject']
    sender = email_data['sender']
    body = email_data.get('body', '')
    
    # Skip LinkedIn notifications completely
    if 'linkedin' in sender.lower() or 'linkedin' in subject.lower():
        logger.info("Skipping LinkedIn notification email")
        return None
        
    # Non-company terms to filter out (cities, generic terms, etc.)
    non_company_terms = [
        # Cities and locations
        'tel aviv', 'new york', 'san francisco', 'london', 'berlin', 'tokyo',
        'paris', 'toronto', 'seattle', 'austin', 'boston', 'chicago', 'israel',
        # Generic terms
        'notification', 'alert', 'message', 'update', 'mail', 'inbox', 
        'admin', 'system', 'support', 'help', 'info', 'no-reply', 'noreply',
        'regarding', 'application', 'jobs', 'opportunities', 'career',
        # Short terms
        'hi', 'hey', 're', 'fw', 'fwd', 'the', 'your', 'our', 'we', 'an',
        # Technical terms
        'smtp', 'email', 'mail', 'server', 'account'
    ]

    def _normalize_company(candidate):
        if not candidate:
            return None
        cleaned = re.sub(r'[\|,;]+$', '', candidate).strip()
        cleaned = re.sub(r'^[\s\-–—]+', '', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = re.split(r'\s[\-–—]\s', cleaned, maxsplit=1)[0].strip()
        cleaned = re.split(r'\b(?:is|has|will|remains|continues|under|about|regarding)\b', cleaned, maxsplit=1)[0].strip()
        cleaned = re.sub(r'\b(?:role|position)\b.*$', '', cleaned, flags=re.IGNORECASE).strip()
        if len(cleaned) < 3:
            return None
        lowered = cleaned.lower()
        if any(term in lowered for term in non_company_terms):
            return None
        return cleaned

    def _return_candidate(value, source):
        company = _normalize_company(value)
        if company:
            logger.info(f"Extracted company from {source}: {company}")
            return company
        return None
    
    # Subject-based patterns like "Thank you for applying to COMPANY"
    subject_patterns = [
        r'(?:application|applying)\s+(?:to|with|at)\s+([A-Z][A-Za-z0-9&\'\- ]{1,50})',
        r'for\s+the\s+[^,]+?\s+(?:position|role)\s+(?:at|with)\s+([A-Z][A-Za-z0-9&\'\- ]{1,50})'
    ]
    for pattern in subject_patterns:
        match = re.search(pattern, subject, re.IGNORECASE)
        if match:
            company = _return_candidate(match.group(1), 'subject pattern')
            if company:
                return company
    
    # Handle "Company - Application Received" style subjects
    if '-' in subject or '|' in subject or '–' in subject or '—' in subject:
        for chunk in re.split(r'[-|–—]', subject):
            if 'application' in chunk.lower():
                possible = chunk.split(' for ')[-1].split(' to ')[-1]
                company = _return_candidate(possible, 'subject chunk')
                if company:
                    return company

    if '|' in subject:
        for candidate in reversed([part.strip() for part in subject.split('|')]):
            company = _return_candidate(candidate, 'subject pipe segment')
            if company:
                return company

    if '/' in subject:
        for candidate in reversed([part.strip() for part in subject.split('/')]):
            company = _return_candidate(candidate, 'subject slash segment')
            if company:
                return company

    combined_text = f"{subject} {body}"
    role_company_pattern = re.search(r'(?:role|position)\s+(?:at|with)\s+([A-Z][A-Za-z0-9&\'\- ]{1,50})', combined_text, re.IGNORECASE)
    if role_company_pattern:
        company = _return_candidate(role_company_pattern.group(1), 'role reference')
        if company:
            return company
    
    # Pattern for company in "Thank you for applying to COMPANY" format
    apply_pattern = re.search(r'thank\s+you\s+for\s+(?:your\s+)?(?:interest|application|applying)\s+(?:to|at|with)\s+([A-Z][A-Za-z0-9&\'\- ]{1,50})', body, re.IGNORECASE)
    if apply_pattern:
        company = _return_candidate(apply_pattern.group(1), 'body confirmation')
        if company:
            return company
    
    # Try from sender with name extraction
    sender_name_match = re.search(r'^([^<@]+?)\s*<', sender)
    if sender_name_match:
        sender_name = sender_name_match.group(1).strip()
        # Look for company patterns in sender name
        company_patterns = [
            r'^([A-Z][A-Za-z0-9]+(?:\s+[A-Za-z0-9]+){0,2})\s+(?:Team|Recruiting|HR|Talent)',
            r'^([A-Z][A-Za-z0-9]+(?:\s+[A-Za-z0-9]+){0,2})$'
        ]
        
        for pattern in company_patterns:
            match = re.search(pattern, sender_name)
            if match:
                company = _return_candidate(match.group(1), 'sender name')
                if company:
                    return company
    
    # Last resort: try to extract domain from sender email
    if '@' in sender:
        try:
            domain = sender.split('@')[1].split('>')[0].strip()
            # Remove common email providers
            if not any(provider in domain.lower() for provider in [
                'gmail.com', 'yahoo', 'hotmail', 'outlook', 'aol', 'icloud',
                'protonmail', 'mail.com', 'zoho', 'linkedin', 'indeed', 'monster'
            ]):
                parts = domain.split('.')
                # Use first part if it seems like a company name
                if len(parts[0]) >= 3:  # Avoid very short names
                    company = _return_candidate(parts[0].title(), 'email domain')
                    if company:
                        return company
        except Exception as e:
            logger.error(f"Error extracting domain: {str(e)}")
    
    logger.info(f"Could not extract valid company name from: {subject}")
    return None

def extract_role(email_data):
    """Extract standardized role from email data"""
    subject = email_data.get('subject', '')
    body = email_data.get('body', '')
    combined_text = (subject + " " + body).lower()
    
    # Try to extract specific role types using regex patterns first
    role_patterns = [
        r'(?:position|role|job)(?: as| for)? ([^,.]{3,70}(?:Engineer|Developer|QA|Manager|Specialist|Analyst)[^,.]{0,30})',
        r'your application for(?: the)? ([^,.]{3,70}(?:Engineer|Developer|QA|Manager|Specialist|Analyst)[^,.]{0,30})',
        r'applied for(?: the)? ([^,.]{3,70}(?:Engineer|Developer|QA|Manager|Specialist|Analyst)[^,.]{0,30})'
    ]
    
    for pattern in role_patterns:
        match = re.search(pattern, subject + " " + body, re.IGNORECASE)
        if match:
            raw_role = match.group(1).strip()
            # Now map to standardized roles
            return standardize_role(raw_role)
    
    # If no specific role found, determine from keywords
    return standardize_role_from_keywords(combined_text)

def standardize_role(raw_role):
    """Convert raw role text to standardized role name"""
    raw_role_lower = raw_role.lower()
    
    # QA roles
    if re.search(r'\bqa\b|\bquality\s+assurance\b', raw_role_lower):
        if re.search(r'\bautomation\b|\bauto\b', raw_role_lower):
            return 'QA Automation Engineer'
        return 'QA Engineer'
    
    # Automation roles
    if re.search(r'\bautomation\b|\bauto\b', raw_role_lower):
        return 'Automation Engineer'
        
    # Developer roles
    if re.search(r'\bdev\b|\bdeveloper\b|\bsoftware\s+eng', raw_role_lower):
        if re.search(r'\bfull\s*stack\b|\bfullstack\b', raw_role_lower):
            return 'Full Stack Developer'
        if re.search(r'\bfront\s*end\b|\bfrontend\b', raw_role_lower):
            return 'Frontend Developer'
        if re.search(r'\bback\s*end\b|\bbackend\b', raw_role_lower):
            return 'Backend Developer'
        return 'Software Developer'
    
    # If role contains "engineer" but isn't one of the above
    if re.search(r'\bengineer\b', raw_role_lower):
        return 'Software Engineer'
    
    # Return original if no mapping found (with some cleanup)
    return raw_role

def standardize_role_from_keywords(text):
    """Determine standard role from keywords in text"""
    # QA related
    if 'qa automation' in text or ('qa' in text and 'automation' in text):
        return 'QA Automation Engineer'
    elif 'qa' in text or 'quality assurance' in text or 'test' in text:
        return 'QA Engineer'
    elif 'automation' in text:
        return 'Automation Engineer'
        
    # Developer related
    elif 'full stack' in text or 'fullstack' in text:
        return 'Full Stack Developer'
    elif 'front end' in text or 'frontend' in text:
        return 'Frontend Developer'
    elif 'back end' in text or 'backend' in text:
        return 'Backend Developer'
    elif any(word in text for word in ['developer', 'software', 'engineer', 'programming']):
        return 'Software Developer'
        
    return "Software Engineer"  # Default role

def parse_date(date_str):
    """Parse email date into database date format"""
    try:
        # Try different formats
        for fmt in ['%a, %d %b %Y %H:%M:%S %z', '%a, %d %b %Y %H:%M:%S %Z']:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
                
        # Just use a generic approach
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(date_str)
        return dt.strftime('%Y-%m-%d')
    except Exception:
        # Fall back to today's date
        return datetime.now().strftime('%Y-%m-%d')

if __name__ == '__main__':
    # Initialize the database
    init_db()
    
    # Only start the scheduler in production mode
    if not app.debug:
        scheduler = init_scheduler()
        logger.info("Background scheduler started in production mode")
    else:
        logger.info("Running in debug mode - scheduler disabled to prevent conflicts")
    
    # Set the logging level to be more verbose
    logger.setLevel(logging.DEBUG)
    
    # Add route and error message for testing Google API
    @app.route('/test_gmail')
    def test_gmail():
        try:
            service = get_gmail_service()
            if not service:
                return jsonify({"status": "error", "message": "Failed to create Gmail service"})
                
            # Try to get email profile
            profile = service.users().getProfile(userId='me').execute()
            
            # Try to list some messages
            messages = service.users().messages().list(userId='me', maxResults=5).execute()
            
            return jsonify({
                "status": "success", 
                "profile": profile,
                "messages_count": len(messages.get('messages', []))
            })
        except Exception as e:
            logger.exception("Gmail test failed")
            return jsonify({"status": "error", "message": str(e)})
    
    @app.route('/test_scan')
    def test_scan():
        """Test scanning functionality without background thread"""
        try:
            # Check authentication
            token_path = 'token.pickle'
            if not os.path.exists(token_path):
                return jsonify({'error': 'Not authenticated with Gmail'}), 401
                
            # Get the monitored email
            conn = get_db_connection()
            cursor = conn.execute("SELECT value FROM settings WHERE key = 'monitored_email'")
            row = cursor.fetchone()
            monitored_email = row['value'] if row else monitored_email
            conn.close()
            
            # Create Gmail service
            service = get_gmail_service()
            if not service:
                return jsonify({'error': 'Failed to initialize Gmail service'}), 500
            
            # Run scan directly (not in thread)
            result = scan_emails_and_process(monitored_email, service)
            
            return jsonify({
                'success': True, 
                'message': f'Scan completed for {monitored_email}',
                'result': result
            })
        except Exception as e:
            logger.error(f"Error in test scan: {str(e)}")
            logger.exception("Stack trace:")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/classify_test')
    def classify_test():
        """Test classification on the last 5 emails for debugging"""
        try:
            # Check authentication
            token_path = 'token.pickle'
            if not os.path.exists(token_path):
                return jsonify({'error': 'Not authenticated with Gmail'}), 401
                    
            # Create Gmail service
            service = get_gmail_service()
            if not service:
                return jsonify({'error': 'Failed to initialize Gmail service'}), 500
            
            # Get some recent emails for testing
            results = service.users().messages().list(
                userId='me',
                maxResults=5
            ).execute()
            
            messages = results.get('messages', [])
            results = []
            
            for msg in messages:
                msg_data = get_email_content(service, msg['id'])
                if not msg_data:
                    continue
                    
                # Try to classify
                classification, debug_info = classify_email_content(msg_data, 'test@example.com')
                
                results.append({
                    'subject': msg_data['subject'],
                    'classification': classification,
                    'debug': debug_info,
                    'is_job_related': bool(classification)
                })
            
            return jsonify({
                'success': True,
                'tested_emails': len(results),
                'results': results
            })
        except Exception as e:
            logger.error(f"Error in classification test: {str(e)}")
            logger.exception("Stack trace:")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/manual_classify/<email_id>')
    def manual_classify(email_id):
        """Manually test classification on a specific email by ID"""
        try:
            # Check authentication
            token_path = 'token.pickle'
            if not os.path.exists(token_path):
                return jsonify({'error': 'Not authenticated with Gmail'}), 401
                    
            # Create Gmail service
            service = get_gmail_service()
            if not service:
                return jsonify({'error': 'Failed to initialize Gmail service'}), 500
            
            # Get specific email
            msg_data = get_email_content(service, email_id)
            if not msg_data:
                return jsonify({'error': 'Could not retrieve email content'}), 404
                    
            # Try to classify
            conn = get_db_connection()
            cursor = conn.execute("SELECT value FROM settings WHERE key = 'monitored_email'")
            row = cursor.fetchone()
            monitored_email = row['value'] if row else monitored_email
            conn.close()
            
            classification, debug_info = classify_email_content(msg_data, monitored_email)
            
            db_result = None
            if classification:
                db_result = update_application_database(classification)
                record_scan_log(
                    msg_data,
                    db_result['result'],
                    db_result.get('message'),
                    {'classification': debug_info, 'source': 'manual_classify'},
                    company=classification['company'],
                    role=classification['role'],
                    status=classification['status']
                )
            
            return jsonify({
                'success': True,
                'subject': msg_data['subject'],
                'classification': classification,
                'debug': debug_info,
                'is_job_related': bool(classification),
                'database_result': db_result
            })
        except Exception as e:
            logger.error(f"Error in manual classification: {str(e)}")
            logger.exception("Stack trace:")
            return jsonify({'error': str(e)}), 500

    # Run the app in debug mode on port 8080
    app.run(host='localhost', port=8080, debug=True)