"""
Database Manager
Handles all database operations for the application.
"""

import sqlite3
import logging
from datetime import datetime
from app.config import Config

logger = logging.getLogger(__name__)

def get_db_connection():
    """Get a connection to the database."""
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database with required tables."""
    try:
        conn = get_db_connection()
        
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
            # Add column without default value first
            conn.execute("ALTER TABLE applications ADD COLUMN status_date TEXT")
            # Then update existing rows
            conn.execute("UPDATE applications SET status_date = date_applied")
            logger.info("Added status_date column to applications table")
        
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
                        ('monitored_email', Config.MONITORED_EMAIL))
        
        conn.commit()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")
        raise
    finally:
        conn.close()

def add_application(data):
    """Add a new application to the database."""
    try:
        # Setting resume_version automatically to the same as role
        resume_version = data['role']
        
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO applications (
                company, role, job_type, country, source, date_applied, resume_version, status, status_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['company'],
            data['role'],
            data['job_type'],
            data['country'],
            data['source'],
            data['date_applied'],
            resume_version,
            data.get('status', 'Pending'),
            datetime.now().strftime('%Y-%m-%d')
        ))
        conn.commit()
        return {'success': True, 'message': 'Application added successfully'}
    
    except Exception as e:
        logger.error(f"Error adding application: {str(e)}")
        return {'success': False, 'error': 'Failed to add application'}
    finally:
        conn.close()

def update_application(data):
    """Update an existing application in the database."""
    try:
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
            return {'success': False, 'error': 'Application not found'}
        
        conn.commit()
        return {'success': True, 'message': 'Application updated successfully'}
    
    except Exception as e:
        logger.error(f"Error updating application: {str(e)}")
        return {'success': False, 'error': 'Failed to update application'}
    finally:
        conn.close()

def update_application_status(data):
    """Update the status of an application."""
    try:
        # Get current date for status update
        today = datetime.now().strftime('%Y-%m-%d')
        
        conn = get_db_connection()
        cursor = conn.execute('''
            UPDATE applications 
            SET status = ?, status_date = ?
            WHERE company = ? AND role = ?
        ''', (data['status'], today, data['company'], data['role']))
        
        if cursor.rowcount == 0:
            return {'success': False, 'error': 'Application not found'}
        
        conn.commit()
        return {
            'success': True, 
            'message': 'Status updated successfully',
            'status_date': today
        }
    
    except Exception as e:
        logger.error(f"Error updating status: {str(e)}")
        return {'success': False, 'error': 'Failed to update status'}
    finally:
        conn.close()

def delete_application(data):
    """Delete an application from the database."""
    try:
        conn = get_db_connection()
        conn.execute('DELETE FROM applications WHERE company = ? AND role = ?',
                     (data['company'], data['role']))
        conn.commit()
        return {'success': True, 'message': 'Application deleted successfully'}
    
    except Exception as e:
        logger.error(f"Error deleting application: {str(e)}")
        return {'success': False, 'error': 'Failed to delete application'}
    finally:
        conn.close()

def get_all_applications():
    """Get all applications from the database."""
    try:
        conn = get_db_connection()
        applications = conn.execute('SELECT * FROM applications ORDER BY id DESC').fetchall()
        return applications
    except Exception as e:
        logger.error(f"Error getting applications: {str(e)}")
        return []
    finally:
        conn.close()

def get_setting(key, default=None):
    """Get a setting from the database."""
    try:
        conn = get_db_connection()
        cursor = conn.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row['value'] if row else default
    except Exception as e:
        logger.error(f"Error getting setting {key}: {str(e)}")
        return default
    finally:
        conn.close()

def update_setting(key, value):
    """Update a setting in the database."""
    try:
        conn = get_db_connection()
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", 
                    (key, value))
        conn.commit()
        return {'success': True, 'message': f'Setting {key} updated successfully'}
    except Exception as e:
        logger.error(f"Error updating setting {key}: {str(e)}")
        return {'success': False, 'error': f'Failed to update setting {key}'}
    finally:
        conn.close()

def update_application_from_email(app_data):
    """Update or add an application from email data."""
    try:
        company = app_data.get('company')
        role = app_data.get('role')
        status = app_data.get('status', 'Pending')
        
        # If company or role is missing, we can't update
        if not company or not role:
            return {'result': 'error', 'message': 'Missing company or role'}
        
        # Current date for status updates
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Connect to database
        conn = get_db_connection()
        
        # Check if application already exists
        cursor = conn.execute(
            "SELECT * FROM applications WHERE LOWER(company) = LOWER(?) AND LOWER(role) = LOWER(?)", 
            (company, role)
        )
        existing = cursor.fetchone()
        
        if existing:
            # Only update if status is different
            if existing['status'] != status:
                conn.execute("""
                    UPDATE applications 
                    SET status = ?, status_date = ?
                    WHERE id = ?
                """, (status, today, existing['id']))
                conn.commit()
                return {'result': 'updated', 'id': existing['id'], 'date': today}
            else:
                return {'result': 'no_change', 'id': existing['id']}
        else:
            # Insert new application
            conn.execute("""
                INSERT INTO applications (
                    company, role, job_type, country, source, date_applied, 
                    resume_version, status, status_date
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                company,
                role,
                app_data.get('job_type', 'Remote'),
                app_data.get('country', 'Unknown'),
                app_data.get('source', 'Email'),
                app_data.get('date_applied', today),
                role,  # Use role as resume version
                status,
                today
            ))
            conn.commit()
            cursor = conn.execute("SELECT last_insert_rowid()")
            last_id = cursor.fetchone()[0]
            return {'result': 'new', 'id': last_id, 'date': today}
    except Exception as e:
        logger.error(f"Error updating application from email: {str(e)}")
        return {'result': 'error', 'message': str(e)}
    finally:
        if 'conn' in locals() and conn:
            conn.close()
