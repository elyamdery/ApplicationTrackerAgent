"""
Web Routes
Defines all web routes for the Flask application.
"""

import os
import pickle
import secrets
import logging
import csv
import json
import threading
from datetime import datetime, timedelta

from flask import render_template, request, jsonify, send_file, redirect, url_for, session
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Use relative imports to avoid circular dependencies
from ..config import Config
from ..database import db_manager
from ..services.gmail_service import GmailService
from ..agents.email_monitor import EmailMonitorAgent
from ..agents.classifier_agent import ClassifierAgent
from ..agents.database_agent import DatabaseAgent
from ..agents.notification_agent import NotificationAgent

# Configure logging
logger = logging.getLogger(__name__)

# Initialize agents
gmail_service = GmailService()
email_monitor_agent = None
classifier_agent = ClassifierAgent()
database_agent = DatabaseAgent()
notification_agent = NotificationAgent()

# Add these variables at the top level of your file
scan_status = {
    'is_scanning': False,
    'start_time': None,
    'end_time': None,
    'status': 'idle',  # idle, scanning, completed, error
    'result': None,
    'error': None
}

def register_routes(app):
    """Register all routes with the Flask app."""

    @app.route('/')
    def index():
        conn = None
        try:
            # Check if credentials exist and are valid
            token_path = Config.TOKEN_PATH
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
            monitored_email = db_manager.get_setting('monitored_email', Config.MONITORED_EMAIL)
            last_scan_time = db_manager.get_setting('last_scan_time')

            # Get applications
            applications = db_manager.get_all_applications()

            return render_template('index.html',
                                  applications=applications,
                                  is_authenticated=is_authenticated,
                                  monitored_email=monitored_email,
                                  last_scan_time=last_scan_time)
        except Exception as e:
            logger.error(f"Error loading index: {str(e)}")
            return jsonify({'error': 'Failed to load applications'}), 500

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
                        "client_id": Config.GOOGLE_CLIENT_ID,
                        "client_secret": Config.GOOGLE_CLIENT_SECRET,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                        "redirect_uris": [Config.GOOGLE_REDIRECT_URI]
                    }
                },
                scopes=Config.GOOGLE_API_SCOPES,
                redirect_uri=Config.GOOGLE_REDIRECT_URI
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
            service = gmail_service.get_service()
            if service:
                email_monitor_agent = EmailMonitorAgent(gmail_service=service)
                return jsonify({'success': 'Agents initialized successfully'})
            else:
                return jsonify({'error': 'Failed to initialize Gmail service'}), 500
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
                        "client_id": Config.GOOGLE_CLIENT_ID,
                        "client_secret": Config.GOOGLE_CLIENT_SECRET,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                        "redirect_uris": [Config.GOOGLE_REDIRECT_URI]
                    }
                },
                scopes=Config.GOOGLE_API_SCOPES,
                redirect_uri=Config.GOOGLE_REDIRECT_URI
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
                with open(Config.TOKEN_PATH, 'wb') as token:
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

    @app.route('/add', methods=['POST'])
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

            result = db_manager.add_application(data)
            if result['success']:
                return jsonify({'success': result['message']})
            else:
                return jsonify({'error': result['error']}), 500

        except Exception as e:
            logger.error(f"Error adding application: {str(e)}")
            return jsonify({'error': 'Failed to add application'}), 500

    @app.route('/delete', methods=['POST'])
    def delete_application():
        try:
            data = request.get_json()
            logger.debug(f"Delete request data: {data}")

            if not data.get('company') or not data.get('role'):
                return jsonify({'error': 'Company and role are required'}), 400

            result = db_manager.delete_application(data)
            if result['success']:
                return jsonify({'success': result['message']})
            else:
                return jsonify({'error': result['error']}), 500

        except Exception as e:
            logger.error(f"Error deleting application: {str(e)}")
            return jsonify({'error': 'Failed to delete application'}), 500

    @app.route('/export')
    def export_to_csv():
        try:
            applications = db_manager.get_all_applications()

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

            result = db_manager.update_application_status(data)
            if result['success']:
                return jsonify({
                    'success': result['message'],
                    'status_date': result['status_date']
                })
            else:
                return jsonify({'error': result['error']}), 500

        except Exception as e:
            logger.error(f"Error updating status: {str(e)}")
            return jsonify({'error': 'Failed to update status'}), 500

    @app.route('/edit', methods=['POST'])
    def edit_application():
        try:
            data = request.get_json()
            logger.debug(f"Edit request data: {data}")

            required_fields = ['original_company', 'original_role', 'company', 'role',
                             'job_type', 'country', 'date_applied', 'source']
            if not all(key in data for key in required_fields):
                return jsonify({'error': 'Missing required fields'}), 400

            result = db_manager.update_application(data)
            if result['success']:
                return jsonify({'success': result['message']})
            else:
                return jsonify({'error': result['error']}), 500

        except Exception as e:
            logger.error(f"Error updating application: {str(e)}")
            return jsonify({'error': 'Failed to update application'}), 500

    @app.route('/clear_token')
    def clear_token():
        """Clear the token file and redirect to auth status"""
        token_path = Config.TOKEN_PATH
        if os.path.exists(token_path):
            os.remove(token_path)
            logger.info("Token file removed")

        # Also clear any session data
        session.clear()

        return redirect(url_for('auth_status'))

    @app.route('/auth_status')
    def auth_status():
        """Show authentication status and debugging information"""
        token_path = Config.TOKEN_PATH
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
            'redirect_uri': Config.GOOGLE_REDIRECT_URI
        }

        # Return HTML template instead of JSON
        return render_template('auth_status.html', auth_info=auth_info)

    @app.route('/settings', methods=['GET'])
    def settings_page():
        """Display settings page with integrated auth status"""
        try:
            # Get the monitored email
            email = db_manager.get_setting('monitored_email', Config.MONITORED_EMAIL)

            # Check authentication status
            token_path = Config.TOKEN_PATH
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

    @app.route('/settings/email', methods=['POST'])
    def update_email():
        """Update monitored email"""
        try:
            data = request.get_json()
            new_email = data.get('email')

            if not new_email or '@' not in new_email:
                return jsonify({'error': 'Invalid email format'}), 400

            result = db_manager.update_setting('monitored_email', new_email)
            if result['success']:
                return jsonify({'success': True, 'message': 'Email updated successfully'})
            else:
                return jsonify({'error': result['error']}), 500
        except Exception as e:
            logger.error(f"Error updating email: {str(e)}")
            return jsonify({'error': 'Failed to update email'}), 500

    @app.route('/scan_now')
    def scan_now():
        """Manually trigger email scanning"""
        global scan_status, gmail_service, email_monitor_agent, classifier_agent, database_agent

        try:
            # Check authentication
            token_path = Config.TOKEN_PATH
            if not os.path.exists(token_path):
                return jsonify({'error': 'Not authenticated with Gmail'}), 401

            # Get the monitored email
            monitored_email = db_manager.get_setting('monitored_email', Config.MONITORED_EMAIL)

            # Update last scan time
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            db_manager.update_setting('last_scan_time', now)

            # Create Gmail service
            service = gmail_service.get_service()
            if not service:
                return jsonify({'error': 'Failed to initialize Gmail service'}), 500

            # Initialize email monitor agent if needed
            if not email_monitor_agent:
                email_monitor_agent = EmailMonitorAgent(gmail_service=service)

            # Update scan status
            scan_status = {
                'is_scanning': True,
                'start_time': now,
                'end_time': None,
                'status': 'scanning',
                'result': None,
                'error': None
            }

            # Run scan in a background thread with timeout protection
            def run_scan():
                global scan_status
                try:
                    # Search for emails
                    messages = gmail_service.search_job_application_emails(
                        days=Config.EMAIL_LOOKBACK_DAYS,
                        target_email=monitored_email
                    )

                    # Process each email
                    processed_count = 0
                    new_count = 0
                    updated_count = 0

                    for msg in messages:
                        # Get email content
                        email_data = gmail_service.get_email_content(msg['id'])
                        if not email_data:
                            continue

                        # Save email for debugging
                        if email_monitor_agent:
                            email_monitor_agent.dump_email_for_debugging(email_data)

                        # Classify email
                        classification = classifier_agent.classify_email(email_data)

                        # Skip if not job related
                        if not classification.get('is_job_related', False):
                            continue

                        # Update email data with classification
                        email_data.update(classification)

                        # Update database
                        result = database_agent.update_application(email_data)

                        if result['result'] == 'new':
                            new_count += 1
                        elif result['result'] == 'updated':
                            updated_count += 1

                        processed_count += 1

                    # Update status with result
                    scan_status['end_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    scan_status['status'] = 'completed'
                    scan_status['result'] = {
                        'processed': processed_count,
                        'new': new_count,
                        'updated': updated_count
                    }
                    scan_status['is_scanning'] = False

                    logger.info(f"Scan completed: processed {processed_count}, new {new_count}, updated {updated_count}")
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
                'message': f'Scanning emails for {monitored_email}',
                'last_scan_time': now
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
            last_scan_time = db_manager.get_setting('last_scan_time')

            # Return the current scan status plus the last scan time
            return jsonify({
                'is_scanning': scan_status['is_scanning'],
                'status': scan_status['status'],
                'start_time': scan_status['start_time'],
                'end_time': scan_status['end_time'],
                'result': scan_status['result'],
                'error': scan_status['error'],
                'last_scan_time': last_scan_time
            })
        except Exception as e:
            logger.error(f"Error getting scan status: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/authenticate')
    def authenticate():
        """Force a new authentication flow"""
        try:
            # Remove existing token if it exists
            token_path = Config.TOKEN_PATH
            if os.path.exists(token_path):
                os.remove(token_path)
                logger.info("Removed existing token.pickle")

            # Get fresh authentication
            service = gmail_service.authenticate()
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
