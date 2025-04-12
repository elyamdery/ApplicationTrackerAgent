"""
Simplified Main Flow
A simplified version of the application with the most critical functionality.
"""

import sys
import os
import sqlite3
import logging
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, session
from flask.sessions import SecureCookieSessionInterface
import secrets

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Set Flask logger to same level
logging.getLogger('werkzeug').setLevel(logging.DEBUG)

# Create Flask app
app = Flask(__name__, static_folder='static', static_url_path='/static')
app.secret_key = secrets.token_hex(16)

# Global variables
scan_status = {
    'is_scanning': False,
    'start_time': None,
    'status': 'idle',  # idle, scanning, completed, error
    'result': None,
    'error': None,
    'emails': []
}
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour
app.session_interface = SecureCookieSessionInterface()

# Add scan status variable
scan_status = {
    'is_scanning': False,
    'start_time': None,
    'end_time': None,
    'status': 'idle',  # idle, scanning, completed, error
    'result': None,
    'error': None
}

# Database functions
def init_db():
    """Initialize the database with required tables."""
    try:
        conn = sqlite3.connect('job_applications.db')

        # Create applications table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT NOT NULL,
                role TEXT NOT NULL,
                job_type TEXT NOT NULL,
                country TEXT NOT NULL,
                source TEXT NOT NULL,
                date_applied TEXT NOT NULL,
                resume_version TEXT NOT NULL,
                status TEXT NOT NULL,
                status_date TEXT
            );
        ''')

        # Check if status_date column exists, add if it doesn't
        cursor = conn.execute("PRAGMA table_info(applications)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'status_date' not in columns:
            conn.execute("ALTER TABLE applications ADD COLUMN status_date TEXT")
            conn.execute("UPDATE applications SET status_date = date_applied")
            logger.info("Added status_date column to applications table")

        # Check if notes column exists, add if it doesn't
        if 'notes' not in columns:
            conn.execute("ALTER TABLE applications ADD COLUMN notes TEXT")
            logger.info("Added notes column to applications table")

        # Add settings table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
        ''')

        # Set default email if it doesn't exist
        cursor = conn.execute("SELECT value FROM settings WHERE key = 'monitored_email'")
        if not cursor.fetchone():
            conn.execute("INSERT INTO settings (key, value) VALUES (?, ?)",
                        ('monitored_email', 'elyamworks@gmail.com'))
        else:
            # Update primary email to elyamworks@gmail.com
            conn.execute("UPDATE settings SET value = ? WHERE key = ?",
                        ('elyamworks@gmail.com', 'monitored_email'))

        # Add additional email
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                    ('additional_email', 'elyam.work@gmail.com'))

        # Add email enabled settings
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                    ('primary_email_enabled', 'true'))
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                    ('additional_email_enabled', 'false'))

        conn.commit()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")
        raise
    finally:
        conn.close()

def get_db_connection():
    """Get a connection to the database."""
    conn = sqlite3.connect('job_applications.db')
    conn.row_factory = sqlite3.Row
    return conn

# Routes
@app.route('/')
def index():
    try:
        # Get applications
        conn = get_db_connection()
        applications = conn.execute('SELECT * FROM applications ORDER BY id DESC').fetchall()

        # Get monitored email
        cursor = conn.execute("SELECT value FROM settings WHERE key = 'monitored_email'")
        row = cursor.fetchone()
        monitored_email = row['value'] if row else 'example@gmail.com'

        # Get last scan time
        cursor = conn.execute("SELECT value FROM settings WHERE key = 'last_scan_time'")
        row = cursor.fetchone()
        last_scan_time = row['value'] if row else None

        # Check if token file exists (for display purposes only)
        token_path = 'token.pickle'
        is_authenticated = os.path.exists(token_path)

        # Log for debugging
        logger.debug(f"Rendering index with: applications={len(applications)}, is_authenticated={is_authenticated}, monitored_email={monitored_email}, last_scan_time={last_scan_time}")

        return render_template('fixed_index.html',
                              applications=applications,
                              is_authenticated=is_authenticated,
                              monitored_email=monitored_email,
                              last_scan_time=last_scan_time)
    except Exception as e:
        logger.error(f"Error loading index: {str(e)}")
        return jsonify({'error': 'Failed to load applications'}), 500
    finally:
        if 'conn' in locals():
            conn.close()

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
        if 'conn' in locals():
            conn.close()

@app.route('/delete', methods=['POST'])
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
        if 'conn' in locals():
            conn.close()

@app.route('/export')
def export_to_csv():
    try:
        import csv

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
        if 'conn' in locals():
            conn.close()

@app.route('/settings', methods=['GET'])
def settings_page():
    """Display settings page"""
    try:
        # Get the monitored email
        conn = get_db_connection()
        cursor = conn.execute("SELECT value FROM settings WHERE key = 'monitored_email'")
        row = cursor.fetchone()
        email = row['value'] if row else 'example@gmail.com'

        # Get additional email
        cursor = conn.execute("SELECT value FROM settings WHERE key = 'additional_email'")
        row = cursor.fetchone()
        additional_email = row['value'] if row else ''

        # Get email enabled settings
        cursor = conn.execute("SELECT value FROM settings WHERE key = 'primary_email_enabled'")
        row = cursor.fetchone()
        primary_email_enabled = row['value'] if row else 'true'

        cursor = conn.execute("SELECT value FROM settings WHERE key = 'additional_email_enabled'")
        row = cursor.fetchone()
        additional_email_enabled = row['value'] if row else 'false'

        # Check if token file exists (for display purposes only)
        token_path = 'token.pickle'
        has_token_file = os.path.exists(token_path)

        # In a real application, we would validate the token
        # For now, we'll just check if the token file exists
        is_authenticated = has_token_file
        credentials_valid = has_token_file

        return render_template(
            'new_settings.html',
            email=email,
            monitored_email=email,
            additional_email=additional_email,
            primary_email_enabled=primary_email_enabled == 'true',
            additional_email_enabled=additional_email_enabled == 'true',
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
        email_type = data.get('type', 'primary')  # 'primary' or 'additional'
        enabled = data.get('enabled')  # Optional, can be None

        if new_email and '@' not in new_email:
            return jsonify({'error': 'Invalid email format'}), 400

        conn = get_db_connection()

        # Determine which email to update
        key = 'monitored_email' if email_type == 'primary' else 'additional_email'
        enabled_key = 'primary_email_enabled' if email_type == 'primary' else 'additional_email_enabled'

        # Update email if provided
        if new_email:
            conn.execute("""
                INSERT OR REPLACE INTO settings (key, value)
                VALUES (?, ?)
            """, (key, new_email))

        # Update enabled status if provided
        if enabled is not None:
            enabled_value = 'true' if enabled else 'false'
            conn.execute("""
                INSERT OR REPLACE INTO settings (key, value)
                VALUES (?, ?)
            """, (enabled_key, enabled_value))

        conn.commit()

        # Get current values for response
        cursor = conn.execute(f"SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        current_email = row['value'] if row else ''

        cursor = conn.execute(f"SELECT value FROM settings WHERE key = ?", (enabled_key,))
        row = cursor.fetchone()
        current_enabled = row['value'] if row else 'true' if email_type == 'primary' else 'false'

        return jsonify({
            'success': True,
            'message': f'{email_type.capitalize()} email settings updated successfully',
            'email': current_email,
            'enabled': current_enabled == 'true',
            'type': email_type
        })
    except Exception as e:
        logger.error(f"Error updating email: {str(e)}")
        return jsonify({'error': 'Failed to update email'}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@app.route('/scan_status')
def get_scan_status():
    """Get the current status of the email scan"""
    try:
        # Get the last scan time from the database
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
            'last_scan_time': last_scan_time
        })
    except Exception as e:
        logger.error(f"Error getting scan status: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/scan_now')
def scan_now():
    """Simulate starting a scan"""
    try:
        import datetime

        # Check if authenticated
        token_path = 'token.pickle'
        is_authenticated = os.path.exists(token_path)

        if not is_authenticated:
            return jsonify({
                'success': False,
                'error': 'Not authenticated with Gmail. Please authenticate in the settings page.'
            }), 401

        # Get emails to scan (only enabled ones)
        conn = get_db_connection()

        # Get primary email if enabled
        cursor = conn.execute("SELECT value FROM settings WHERE key = 'primary_email_enabled'")
        row = cursor.fetchone()
        primary_enabled = row['value'] == 'true' if row else True

        # Get additional email if enabled
        cursor = conn.execute("SELECT value FROM settings WHERE key = 'additional_email_enabled'")
        row = cursor.fetchone()
        additional_enabled = row['value'] == 'true' if row else False

        emails = []

        # Add primary email if enabled
        if primary_enabled:
            cursor = conn.execute("SELECT value FROM settings WHERE key = 'monitored_email'")
            row = cursor.fetchone()
            if row and row['value']:
                emails.append(row['value'])

        # Add additional email if enabled
        if additional_enabled:
            cursor = conn.execute("SELECT value FROM settings WHERE key = 'additional_email'")
            row = cursor.fetchone()
            if row and row['value']:
                emails.append(row['value'])

        # Check if we have any emails to scan
        if not emails:
            return jsonify({
                'success': False,
                'error': 'No enabled emails to scan. Please enable at least one email in settings.'
            }), 400

        # Update scan status
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        scan_status['is_scanning'] = True
        scan_status['start_time'] = now
        scan_status['status'] = 'scanning'
        scan_status['result'] = None
        scan_status['error'] = None
        scan_status['emails'] = emails

        # Update last scan time in database
        conn.execute("""
            INSERT OR REPLACE INTO settings (key, value)
            VALUES ('last_scan_time', ?)
        """, (now,))
        conn.commit()
        conn.close()

        # Log the emails being scanned
        logger.info(f"Starting scan for emails: {', '.join(emails)}")

        # Simulate a scan completing after a few seconds
        import threading
        def complete_scan():
            import time, random

            # Simulate processing time based on number of emails
            time.sleep(len(emails) * 2)

            # Generate random results for each email
            email_results = {}
            total_processed = 0
            total_new = 0
            total_updated = 0

            for email in emails:
                processed = random.randint(3, 10)
                new = random.randint(0, 2)
                updated = random.randint(0, 2)

                email_results[email] = {
                    'processed': processed,
                    'new': new,
                    'updated': updated
                }

                total_processed += processed
                total_new += new
                total_updated += updated

            # Update scan status
            scan_status['is_scanning'] = False
            scan_status['end_time'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            scan_status['status'] = 'completed'
            scan_status['result'] = {
                'processed': total_processed,
                'new': total_new,
                'updated': total_updated,
                'email_results': email_results
            }

            logger.info(f"Scan completed: processed {total_processed}, new {total_new}, updated {total_updated}")

        thread = threading.Thread(target=complete_scan)
        thread.daemon = True
        thread.start()

        return jsonify({
            'success': True,
            'message': f'Scanning {len(emails)} email(s)...',
            'emails': emails,
            'last_scan_time': now
        })
    except Exception as e:
        logger.error(f"Error starting scan: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/start_auth')
def start_auth():
    """Start the Gmail authentication process"""
    try:
        logger.info("Starting authentication process")

        # In a real application, this would redirect to Google's OAuth consent screen
        # For now, we'll simulate the authentication process

        # Create a dummy token file
        import pickle
        token_data = {
            'token': 'dummy_token',
            'refresh_token': 'dummy_refresh_token',
            'token_uri': 'https://oauth2.googleapis.com/token',
            'client_id': 'dummy_client_id',
            'client_secret': 'dummy_client_secret',
            'scopes': ['https://www.googleapis.com/auth/gmail.readonly']
        }

        token_path = 'token.pickle'
        with open(token_path, 'wb') as token_file:
            pickle.dump(token_data, token_file)

        logger.info(f"Created dummy token file at {token_path}")

        # In a real application, we would redirect to Google's OAuth consent screen
        # and then handle the callback with a route like /oauth2callback

        # For now, redirect to auth status page
        logger.info("Redirecting to auth status page")
        return redirect(url_for('auth_status'))
    except Exception as e:
        logger.error(f"Error starting authentication: {str(e)}")
        return jsonify({'error': 'Failed to start authentication'}), 500

@app.route('/oauth2callback')
def oauth2callback():
    """Handle the OAuth callback from Google"""
    # In a real application, this would handle the callback from Google
    # and exchange the authorization code for an access token

    # For now, redirect to auth status page
    return redirect(url_for('auth_status'))

@app.route('/guide')
def guide():
    """Display the user guide"""
    # Check if token file exists (for display purposes only)
    token_path = 'token.pickle'
    is_authenticated = os.path.exists(token_path)

    # Get monitored email
    conn = get_db_connection()
    cursor = conn.execute("SELECT value FROM settings WHERE key = 'monitored_email'")
    row = cursor.fetchone()
    monitored_email = row['value'] if row else 'example@gmail.com'

    # Get last scan time
    cursor = conn.execute("SELECT value FROM settings WHERE key = 'last_scan_time'")
    row = cursor.fetchone()
    last_scan_time = row['value'] if row else None

    conn.close()

    return render_template('new_guide.html',
                          is_authenticated=is_authenticated,
                          monitored_email=monitored_email,
                          last_scan_time=last_scan_time)

# API Routes for Applications
@app.route('/api/applications', methods=['GET'])
def get_applications():
    """Get all applications"""
    try:
        conn = get_db_connection()
        applications = conn.execute('SELECT * FROM applications ORDER BY id DESC').fetchall()

        # Convert to list of dicts
        result = []
        for app in applications:
            app_dict = {}
            for key in app.keys():
                app_dict[key] = app[key]
            result.append(app_dict)

        return jsonify({
            'success': True,
            'applications': result
        })
    except Exception as e:
        logger.error(f"Error getting applications: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to get applications'}), 500
    finally:
        if 'conn' in locals() and conn:
            conn.close()

@app.route('/api/applications', methods=['POST'])
def create_application():
    """Create a new application"""
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['company', 'role', 'date_applied', 'status']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400

        conn = get_db_connection()
        cursor = conn.execute("""
            INSERT INTO applications (company, role, job_type, country, source, date_applied, resume_version, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data['company'],
            data['role'],
            data.get('job_type', 'Full-time'),  # Default values for required fields
            data.get('country', 'United States'),
            data.get('source', 'Manual Entry'),
            data['date_applied'],
            data.get('resume_version', data['role']),  # Use role as default resume version
            data['status'],
            data.get('notes', '')
        ))

        conn.commit()

        # Get the ID of the newly created application
        app_id = cursor.lastrowid

        return jsonify({
            'success': True,
            'message': 'Application created successfully',
            'id': app_id
        })
    except Exception as e:
        logger.error(f"Error creating application: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to create application'}), 500
    finally:
        if 'conn' in locals() and conn:
            conn.close()

@app.route('/api/applications/<int:app_id>', methods=['GET'])
def get_application(app_id):
    """Get a specific application"""
    try:
        conn = get_db_connection()
        app = conn.execute('SELECT * FROM applications WHERE id = ?', (app_id,)).fetchone()

        if not app:
            return jsonify({'success': False, 'error': 'Application not found'}), 404

        # Convert to dict
        app_dict = {}
        for key in app.keys():
            app_dict[key] = app[key]

        return jsonify({
            'success': True,
            'application': app_dict
        })
    except Exception as e:
        logger.error(f"Error getting application: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to get application'}), 500
    finally:
        if 'conn' in locals() and conn:
            conn.close()

@app.route('/api/applications/<int:app_id>', methods=['PUT'])
def update_application(app_id):
    """Update a specific application"""
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['company', 'role', 'date_applied', 'status']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400

        conn = get_db_connection()

        # Check if application exists
        app = conn.execute('SELECT * FROM applications WHERE id = ?', (app_id,)).fetchone()
        if not app:
            return jsonify({'success': False, 'error': 'Application not found'}), 404

        # Update application
        conn.execute("""
            UPDATE applications
            SET company = ?, role = ?, job_type = ?, country = ?, source = ?,
                date_applied = ?, resume_version = ?, status = ?, notes = ?
            WHERE id = ?
        """, (
            data['company'],
            data['role'],
            data.get('job_type', app['job_type']),  # Use existing value if not provided
            data.get('country', app['country']),
            data.get('source', app['source']),
            data['date_applied'],
            data.get('resume_version', app['resume_version']),
            data['status'],
            data.get('notes', app['notes'] if app['notes'] else ''),
            app_id
        ))

        conn.commit()

        return jsonify({
            'success': True,
            'message': 'Application updated successfully'
        })
    except Exception as e:
        logger.error(f"Error updating application: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to update application'}), 500
    finally:
        if 'conn' in locals() and conn:
            conn.close()

@app.route('/api/applications/<int:app_id>', methods=['DELETE'])
def delete_application_by_id(app_id):
    """Delete a specific application"""
    try:
        conn = get_db_connection()

        # Check if application exists
        app = conn.execute('SELECT * FROM applications WHERE id = ?', (app_id,)).fetchone()
        if not app:
            return jsonify({'success': False, 'error': 'Application not found'}), 404

        # Delete application
        conn.execute('DELETE FROM applications WHERE id = ?', (app_id,))
        conn.commit()

        return jsonify({
            'success': True,
            'message': 'Application deleted successfully'
        })
    except Exception as e:
        logger.error(f"Error deleting application: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to delete application'}), 500
    finally:
        if 'conn' in locals() and conn:
            conn.close()

@app.route('/export_csv')
def export_csv():
    """Export applications to CSV"""
    try:
        conn = get_db_connection()
        applications = conn.execute('SELECT * FROM applications ORDER BY id DESC').fetchall()

        # Create CSV file
        import csv
        import io
        from flask import Response

        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        if applications:
            writer.writerow(applications[0].keys())

        # Write data
        for app in applications:
            writer.writerow(app)

        # Create response
        response = Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': 'attachment; filename=applications.csv',
                'Content-Type': 'text/csv'
            }
        )

        return response
    except Exception as e:
        logger.error(f"Error exporting CSV: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to export CSV'}), 500
    finally:
        if 'conn' in locals() and conn:
            conn.close()

# Scan status route is defined above

@app.route('/auth_status')
def auth_status():
    """Show authentication status and debugging information"""
    token_path = 'token.pickle'
    has_token = os.path.exists(token_path)

    auth_info = {
        'has_token_file': has_token,
        'credentials_valid': has_token,  # In a real app, we would validate the token
        'session_contains_state': False,
        'session_keys': [],
        'redirect_uri': 'http://localhost:8080/oauth2callback'
    }

    # Return HTML template
    return render_template('auth_status.html', auth_info=auth_info)

@app.route('/clear_token')
def clear_token():
    """Clear the token file and redirect to auth status"""
    token_path = 'token.pickle'
    if os.path.exists(token_path):
        os.remove(token_path)
        logger.info("Token file removed")

    # Redirect to auth status page
    return redirect(url_for('auth_status'))

if __name__ == '__main__':
    # Initialize the database
    init_db()

    # Run the application
    logger.info("Starting Flask application")
    app.run(host='0.0.0.0', port=8080, debug=True)
