# Job Applications Tracker

## Section 1: Current Features

An intelligent application tracking system with automated email monitoring capabilities.

### Core Features
- Add and manage job applications
- Track application statuses
- Export data to CSV
- Search functionality
- Color-coded status tracking
- Responsive design

### Installation

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

4. **Initialize the database**
```bash
python MainFlow.py
```

5. **Access the application**
- Open http://localhost:5000 in your browser

### Current Usage

#### Application Management
- Add new applications
- Update status manually
- Search and filter applications
- Export data to CSV
- Delete applications & Edit existing applications

#### Status Tracking
- Pending (Grey)
- Interview (Green)
- Assignment (Blue)
- Rejected (Red)
- Offer (Bold Green)

---

## Section 2: Intelligent Agent System (In Development)

> **Note:** This feature is currently under active development and will be released in the coming weeks. The following section describes the planned functionality and architecture.

### Multi-Agent Architecture
Our upcoming intelligent system will utilize multiple specialized agents to automate the job application tracking process:

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

### Technical Implementation

#### Planned Dependencies
```txt
aiohttp==3.8.1
asyncio==3.4.3
google-api-python-client==2.86.0
nltk==3.8.1
scikit-learn==1.2.2
flask-mail==0.9.1
```

### Development Timeline
- Phase 1: Email monitoring setup (2 weeks)
- Phase 2: Classification system (2 weeks)
- Phase 3: Database integration (1 week)
- Phase 4: Notification system (1 week)
- Phase 5: Testing and optimization (2 weeks)

### Benefits of Agent System (Upcoming)
1. **Parallel Processing**
   - Multiple applications tracked simultaneously
   - Non-blocking operations
   - Improved performance

2. **Modular Design**
   - Independent agent functionality
   - Easy maintenance
   - Simple testing
   - Scalable architecture

3. **Intelligent Processing**
   - Machine learning integration
   - Pattern recognition
   - Adaptive behavior
   - Improved accuracy over time

### Future Enhancements
- Additional email provider support
- Advanced ML models
- Custom agent creation
- Analytics dashboard

>Created By Elyam Dery
