# Job Applications Tracker

An intelligent application tracking system with automated email monitoring capabilities.

## Project Structure

The project has been refactored to follow a more modular and maintainable structure:

```
app/
├── __init__.py           # Package initialization
├── config.py             # Configuration settings
├── agents/               # Agent modules
│   ├── __init__.py
│   ├── classifier_agent.py
│   ├── database_agent.py
│   ├── email_monitor.py
│   └── notification_agent.py
├── database/             # Database operations
│   ├── __init__.py
│   └── db_manager.py
├── services/             # External services
│   ├── __init__.py
│   └── gmail_service.py
├── utils/                # Utility functions
│   ├── __init__.py
│   └── logger.py
└── web/                  # Web application
    ├── __init__.py
    ├── app.py
    └── routes.py
```

## Features

### Core Features
- Add and manage job applications
- Track application statuses
- Export data to CSV
- Search functionality
- Color-coded status tracking
- Responsive design

### Intelligent Agent System
- **Email Monitor Agent**: Monitors inbox for job-related emails
- **Classifier Agent**: Analyzes email content and extracts relevant information
- **Database Agent**: Manages data persistence and updates application records
- **Notification Agent**: Sends real-time alerts and status summaries

## Installation

### Prerequisites
- **Python 3.9+**
- **Pip**

### Steps

1. **Clone the repository**
    ```bash
    git clone https://github.com/yourusername/ApplicationTracker.git
    cd ApplicationTracker
    ```

2. **Create a virtual environment**
    ```bash
    python -m venv venv
    .\venv\Scripts\activate
    ```

3. **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4. **Set Up Google Console**
    - Go to the Google Cloud Console → Create a project → Enable the Gmail API.
    - Download your OAuth credentials and save them as `credentials.json` in the project root.
    - Make sure you have redirect URIs set to http://localhost:8090 or similar.

5. **Initialize the database**
    ```bash
    python run.py
    ```

6. **Access the application**
    - Open http://localhost:8080 in your browser

## Usage

### Home Screen
- Displays recent applications in a table.
- Shows whether OCR/Gmail scanning is connected.

### Add / Edit Applications
- Use the “Add” button or “Edit” option to update existing entries.

### Manual Scanning
- Click “Scan Now” if you want an immediate Gmail scan.
- Check “Scan Status” to see if scanning is in progress.

### Automated Scanning
- A background scheduler checks new emails hourly by default (configurable in code).

### Email Notifications (Optional)
- If you want to re-enable them, generate a Google App Password and update `.env`.
- Uncomment the lines in `scan_and_update_applications` that send the notification emails.

### Summary Emails
- Daily summary at 10:00 AM by default (configured in the scheduler).
- Uses GPT-based summarization; keep your OpenAI API key in `.env`.

## Troubleshooting

- **OAuth Error**: Ensure `credentials.json` is valid and redirect URIs match.
- **ModuleNotFoundError**: Check `PYTHONPATH` or install missing packages with `pip`.
- **Database Errors**: Delete `job_applications.db` if schema changes are needed, then rerun.
- **SMTP Auth Failures**: Generate a Google App Password (if using Gmail) and update `.env`.

## Intelligent Agent System

### Multi-Agent Architecture
The application uses a multi-agent architecture to automate the job application tracking process:

#### 1. Email Monitor Agent
- Continuously monitors inbox
- Detects new job-related emails
- Identifies application confirmations
- Routes emails to appropriate agents

#### 2. Classifier Agent
- Analyzes email content
- Determines email type and intent
- Extracts relevant information
- Updates application status

#### 3. Database Agent
- Manages data persistence
- Updates application records
- Maintains status history
- Handles concurrent updates

#### 4. Notification Agent
- Sends real-time alerts
- Manages user preferences
- Handles email notifications
- Provides status summaries

### Benefits of the Agent System
1. **Modular Design**
   - Independent agent functionality
   - Easy maintenance
   - Simple testing
   - Scalable architecture

2. **Intelligent Processing**
   - AI-based classification
   - Pattern recognition
   - Adaptive behavior
   - Improved accuracy over time

### Future Enhancements
- Additional email provider support
- Advanced ML models
- Custom agent creation
- Analytics dashboard

>Created By Elyam Dery
