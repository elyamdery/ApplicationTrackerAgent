"""
Migration Script
Helps migrate from the old structure to the new structure.
"""

import os
import shutil
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_directories():
    """Create the new directory structure."""
    directories = [
        'app',
        'app/agents',
        'app/database',
        'app/services',
        'app/utils',
        'app/web',
        'app/web/static',
        'app/web/templates',
        'logs'
    ]
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            logger.info(f"Created directory: {directory}")

def copy_static_files():
    """Copy static files to the new structure."""
    if os.path.exists('static'):
        for item in os.listdir('static'):
            src = os.path.join('static', item)
            dst = os.path.join('app/web/static', item)
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)
        logger.info("Copied static files")

def copy_templates():
    """Copy template files to the new structure."""
    if os.path.exists('templates'):
        for item in os.listdir('templates'):
            src = os.path.join('templates', item)
            dst = os.path.join('app/web/templates', item)
            shutil.copy2(src, dst)
        logger.info("Copied template files")

def copy_database():
    """Copy database file to the new structure."""
    if os.path.exists('job_applications.db'):
        shutil.copy2('job_applications.db', 'job_applications.db')
        logger.info("Copied database file")

def main():
    """Run the migration script."""
    logger.info("Starting migration")
    
    # Create directories
    create_directories()
    
    # Copy files
    copy_static_files()
    copy_templates()
    copy_database()
    
    logger.info("Migration completed successfully")

if __name__ == '__main__':
    main()
