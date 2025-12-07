import importlib
import os
from datetime import datetime

import pytest


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test_job_applications.db"
    monkeypatch.setenv('JOB_APPS_DB_PATH', str(db_path))

    import utils.db_utils as db_utils
    import MainFlow

    importlib.reload(db_utils)
    importlib.reload(MainFlow)

    MainFlow.init_db()
    with MainFlow.app.test_client() as test_client:
        yield test_client


def _create_payload(**overrides):
    today = datetime.now().strftime('%Y-%m-%d')
    base = {
        'company': 'Acme Corp',
        'role': 'QA Eng',
        'job_type': 'Remote',
        'country': 'IL',
        'date_applied': today,
        'source': 'LinkedIn'
    }
    base.update(overrides)
    return base


def test_add_application_creates_record(client):
    response = client.post('/add_application', json=_create_payload())
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] == 'Application added successfully'

    from utils.db_utils import get_db_connection

    conn = get_db_connection()
    row = conn.execute("SELECT * FROM applications WHERE company = ?", ('Acme Corp',)).fetchone()
    conn.close()
    assert row is not None
    assert row['role'] == 'QA Eng'


def test_edit_application_updates_fields(client):
    client.post('/add_application', json=_create_payload(company='Globex', role='QA Eng'))

    edit_payload = {
        'original_company': 'Globex',
        'original_role': 'QA Eng',
        'company': 'Globex Ltd',
        'role': 'QA Automation Eng',
        'job_type': 'Hybrid',
        'country': 'IL',
        'date_applied': datetime.now().strftime('%Y-%m-%d'),
        'source': 'Website'
    }

    resp = client.post('/edit_application', json=edit_payload)
    assert resp.status_code == 200
    assert resp.get_json()['success'] == 'Application updated successfully'

    from utils.db_utils import get_db_connection

    conn = get_db_connection()
    row = conn.execute("SELECT * FROM applications WHERE company = ?", ('Globex Ltd',)).fetchone()
    conn.close()
    assert row is not None
    assert row['job_type'] == 'Hybrid'
    assert row['source'] == 'Website'


def test_delete_application_removes_record(client):
    client.post('/add_application', json=_create_payload(company='DeleteMe', role='QA Eng'))

    resp = client.post('/delete_application', json={'company': 'DeleteMe', 'role': 'QA Eng'})
    assert resp.status_code == 200
    assert resp.get_json()['success'] == 'Application deleted successfully'

    from utils.db_utils import get_db_connection

    conn = get_db_connection()
    row = conn.execute("SELECT * FROM applications WHERE company = ?", ('DeleteMe',)).fetchone()
    conn.close()
    assert row is None


def test_update_status_sets_status_date(client):
    today = datetime.now().strftime('%Y-%m-%d')
    client.post('/add_application', json=_create_payload(company='StatusCorp', role='QA Eng', date_applied=today))

    resp = client.post('/update_status', json={
        'company': 'StatusCorp',
        'role': 'QA Eng',
        'status': 'Interview'
    })

    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload['success'] == 'Status updated successfully'
    assert payload['status_date'] == today

    from utils.db_utils import get_db_connection

    conn = get_db_connection()
    row = conn.execute(
        "SELECT status, status_date FROM applications WHERE company = ?", ('StatusCorp',)
    ).fetchone()
    conn.close()
    assert row['status'] == 'Interview'
    assert row['status_date'] == today


def test_filter_applications_by_status(client):
    today = datetime.now().strftime('%Y-%m-%d')
    client.post('/add_application', json=_create_payload(company='Alpha', role='QA Eng', date_applied=today))
    client.post('/add_application', json=_create_payload(company='Beta', role='QA Eng', date_applied=today))

    client.post('/update_status', json={
        'company': 'Beta',
        'role': 'QA Eng',
        'status': 'Interview'
    })

    resp = client.post('/filter_applications', json={'status': 'Interview'})
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload['success'] is True
    assert payload['filtered_count'] == 1
    assert payload['applications'][0]['company'] == 'Beta'


def test_update_scan_window_setting(client):
    resp = client.post('/settings/scan_window', json={'window': 'daily'})
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload['days'] == 1

    from utils.db_utils import get_db_connection

    conn = get_db_connection()
    row = conn.execute("SELECT value FROM settings WHERE key = 'scan_window_days'").fetchone()
    conn.close()
    assert row['value'] == '1'


def test_update_scan_window_rejects_invalid_option(client):
    resp = client.post('/settings/scan_window', json={'window': 'monthly'})
    assert resp.status_code == 400


def test_scan_logs_endpoint_returns_entries(client):
    from utils.db_utils import get_db_connection

    conn = get_db_connection()
    conn.execute(
        """
        INSERT INTO scan_logs (email_id, subject, sender, company, role, status_value, outcome, reason, metadata, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            'email-1',
            'Subject',
            'sender@example.com',
            'Acme Corp',
            'QA Eng',
            'Pending',
            'new',
            'inserted',
            '{}',
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
    )
    conn.commit()
    conn.close()

    resp = client.get('/scan_logs?limit=5')
    assert resp.status_code == 200
    payload = resp.get_json()
    assert 'logs' in payload
    assert len(payload['logs']) >= 1
    assert payload['logs'][0]['company'] == 'Acme Corp'


def test_guide_route_renders_successfully(client):
    response = client.get('/guide')
    assert response.status_code == 200
    assert b'User Guide' in response.data
