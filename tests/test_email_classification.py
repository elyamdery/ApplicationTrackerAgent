import importlib

import pytest


@pytest.fixture()
def mainflow_module(monkeypatch):
    monkeypatch.setenv('SKIP_EMAIL_DUMPS', '1')
    import MainFlow

    importlib.reload(MainFlow)
    return MainFlow


def test_classify_email_detects_confirmation(mainflow_module):
    email_data = {
        'id': 'test-1',
        'subject': 'Thank you for applying to Unity Technologies',
        'sender': 'Unity Recruiting Team <no-reply@unity3d.com>',
        'date': 'Sat, 22 Mar 2025 11:13:02 +0000',
        'body': (
            'Hello, thank you for your interest and application to our '
            'Games QA Engineer position at Unity. Our team is reviewing '
            'your application and will contact you with next steps.'
        )
    }

    result, debug_info = mainflow_module.classify_email_content(email_data, 'elyamworks@gmail.com')
    assert result is not None
    assert debug_info['reason'] == 'classified'
    assert result['company'] == 'Unity Technologies'
    assert result['status'] == 'Pending'


def test_classify_email_handles_keyword_signal(mainflow_module):
    email_data = {
        'id': 'test-2',
        'subject': 'Application update - Senior Backend Developer at ExampleCorp',
        'sender': 'Talent Team <careers@examplecorp.com>',
        'date': 'Fri, 21 Mar 2025 08:00:00 +0000',
        'body': (
            'Hi Elyam, your application for the Senior Backend Developer role '
            'at ExampleCorp is under review. We appreciate your interest and '
            'will be in touch regarding next steps.'
        )
    }

    result, debug_info = mainflow_module.classify_email_content(email_data, 'elyamworks@gmail.com')
    assert result is not None
    assert debug_info['reason'] == 'classified'
    assert result['company'] == 'ExampleCorp'
    assert result['status'] == 'Pending'
    assert result['role']


def test_classify_email_infers_hybrid_job_type(mainflow_module):
    email_data = {
        'id': 'test-3',
        'subject': 'Thank you for applying to Workiz - Interview steps',
        'sender': 'Workiz Recruiting <talent@workiz.com>',
        'date': 'Thu, 20 Mar 2025 09:30:00 +0000',
        'body': (
            'Thank you for applying to the Full Stack Engineer position at Workiz. '
            'Our team offers a hybrid schedule splitting time between the Tel Aviv '
            'office and remote work. We will review your application and follow up '
            'with interview scheduling soon.'
        )
    }

    result, debug_info = mainflow_module.classify_email_content(email_data, 'elyamworks@gmail.com')
    assert result is not None
    assert debug_info['reason'] == 'classified'
    assert result['company'] == 'Workiz'
    assert result['job_type'] == 'Hybrid'
