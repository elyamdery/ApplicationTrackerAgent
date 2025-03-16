from flask import Flask, render_template, request, jsonify, send_file
import sqlite3
import csv
import os
import logging
from apscheduler.schedulers.background import BackgroundScheduler
import openai
from datetime import datetime, timedelta
from agents.email_monitor import EmailMonitorAgent

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static', static_url_path='/static')

# Initialize Email Monitor Agent
email_monitor_agent = EmailMonitorAgent()

# Function to initialize the database
def init_db():
    try:
        conn = sqlite3.connect('job_applications.db')
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
                status TEXT NOT NULL
            );
        ''')
        conn.commit()
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")
        raise
    finally:
        conn.close()

# Function to get DB connection
def get_db_connection():
    conn = sqlite3.connect('job_applications.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    try:
        conn = get_db_connection()
        applications = conn.execute('SELECT * FROM applications ORDER BY id DESC').fetchall()
        return render_template('index.html', applications=applications)
    except Exception as e:
        logger.error(f"Error loading index: {str(e)}")
        return jsonify({'error': 'Failed to load applications'}), 500
    finally:
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
        conn.close()

@app.route('/export')
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
        
        conn = get_db_connection()
        cursor = conn.execute('''
            UPDATE applications 
            SET status = ? 
            WHERE company = ? AND role = ?
        ''', (data['status'], data['company'], data['role']))
        
        if cursor.rowcount == 0:
            return jsonify({'error': 'Application not found'}), 404
        
        conn.commit()
        return jsonify({'success': 'Status updated successfully'})
    
    except Exception as e:
        logger.error(f"Error updating status: {str(e)}")
        return jsonify({'error': 'Failed to update status'}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@app.route('/edit', methods=['POST'])
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

# Function to scan emails and update applications
async def scan_and_update_applications():
    try:
        emails = await email_monitor_agent.scan_emails(lookback_days=1)
        conn = get_db_connection()
        for email in emails:
            # Process email and update or add application
            logger.info(f"Processing email: {email['subject']}")
            subject = email.get('subject')
            sender = email.get('from')
            body = email.get('body')

            # Determine the status based on the email content
            status = 'Pending'
            if 'interview' in body.lower():
                status = 'Interview'
            elif 'offer' in body.lower():
                status = 'Offer'
            elif 'rejection' in body.lower():
                status = 'Rejected'

            # Check if the application already exists
            cursor = conn.execute('SELECT * FROM applications WHERE company = ? AND role = ?', (sender, subject))
            application = cursor.fetchone()

            if application:
                # Update existing application status
                conn.execute('UPDATE applications SET status = ? WHERE company = ? AND role = ?', (status, sender, subject))
            else:
                # Add new application
                conn.execute('INSERT INTO applications (company, role, job_type, country, source, date_applied, resume_version, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (sender, subject, 'Unknown', 'Unknown', 'Email', datetime.now().strftime('%Y-%m-%d'), subject, status))

        conn.commit()
    except Exception as e:
        logger.error(f"Error scanning and updating applications: {str(e)}")
    finally:
        if 'conn' in locals():
            conn.close()

# Function to send summary email
def send_summary_email():
    try:
        conn = get_db_connection()
        applications = conn.execute('SELECT * FROM applications WHERE date_applied >= ?', 
                                    (datetime.now() - timedelta(days=1),)).fetchall()
        summary = "Summary of new applications:\n\n"
        for app in applications:
            summary += f"Company: {app['company']}, Role: {app['role']}, Status: {app['status']}\n"
        
        # Use ChatGPT to summarize the updates
        openai.api_key = os.getenv("OPENAI_API_KEY")
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=f"Summarize the following updates:\n{summary}",
            max_tokens=150
        )
        summary = response.choices[0].text.strip()
        
        # Send the summary email
        # This is a placeholder for the actual email sending logic
        logger.info(f"Sending summary email: {summary}")
    except Exception as e:
        logger.error(f"Error sending summary email: {str(e)}")
    finally:
        if 'conn' in locals():
            conn.close()

# Schedule the scan_and_update_applications function to run every hour
scheduler = BackgroundScheduler()
scheduler.add_job(scan_and_update_applications, 'interval', hours=1)
scheduler.start()

# Schedule the send_summary_email function to run every day at 10 AM
scheduler.add_job(send_summary_email, 'cron', hour=10)
scheduler.start()

if __name__ == '__main__':
    # Initialize the database
    init_db()
    # Run the app in debug mode
    app.run(debug=True)