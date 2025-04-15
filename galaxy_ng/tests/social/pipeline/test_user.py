import os
import sys

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'galaxy_ng.settings')
# Add project root to path if needed
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import django
django.setup()

import pytest
from unittest import mock
from galaxy_ng.app.models.auth import User
from galaxy_ng.app.utils.galaxy import generate_unverified_email
from galaxy_ng.social.pipeline import user

@pytest.fixture
def mock_strategy():
    strategy = mock.Mock()
    strategy.create_user.return_value = mock.Mock()
    return strategy

@pytest.fixture
def mock_backend():
    backend = mock.Mock()
    backend.setting.return_value = ['username', 'email']
    return backend

@pytest.fixture
def mock_user():
    return User.objects.create(username='test_user', email='test_user@example.com')

@pytest.fixture
def mock_details():
    return {'username': 'test_user', 'email': 'test_user@example.com'}

@pytest.fixture
def mock_response():
    return {'id': 'test_id'}

def test_get_username(mock_strategy, mock_details):
    result = user.get_username(mock_strategy, mock_details, mock_backend())
    assert result == {'username': 'test_user'}

def test_get_username_no_username(mock_strategy, mock_details):
    mock_details['username'] = None
    result = user.get_username(mock_strategy, mock_details, mock_backend())
    assert result == {'username': None}

def test_create_user_user_exists(mock_strategy, mock_user, mock_details):
    result = user.create_user(mock_strategy, mock_details, mock_backend(), user=mock_user)
    assert result == {'is_new': False, 'user': mock_user}

def test_create_user_user_exists_different_username(mock_strategy, mock_user, mock_details):
    mock_user.username = 'old_username'
    result = user.create_user(mock_strategy, mock_details, mock_backend(), user=mock_user)
    assert result == {'is_new': False, 'user': mock_user}

def test_create_user_user_exists_different_email(mock_strategy, mock_user, mock_details):
    mock_user.email = 'old_email'
    result = user.create_user(mock_strategy, mock_details, mock_backend(), user=mock_user)
    assert result == {'is_new': False, 'user': mock_user}

def test_create_user_user_not_found(mock_strategy, mock_details):
    result = user.create_user(mock_strategy, mock_details, mock_backend())
    assert result == {'is_new': True, 'user': mock_strategy.create_user.return_value}

def test_create_user_user_not_found_different_username(mock_strategy, mock_details):
    mock_details['username'] = 'different_username'
    result = user.create_user(mock_strategy, mock_details, mock_backend())
    assert result == {'is_new': True, 'user': mock_strategy.create_user.return_value}

def test_create_user_user_not_found_different_email(mock_strategy, mock_details):
    mock_details['email'] = 'different_email'
    result = user.create_user(mock_strategy, mock_details, mock_backend())
    assert result == {'is_new': True, 'user': mock_strategy.create_user.return_value}

def test_create_user_user_not_found_different_username_and_email(mock_strategy, mock_details):
    mock_details['username'] = 'different_username'
    mock_details['email'] = 'different_email'
    result = user.create_user(mock_strategy, mock_details, mock_backend())
    assert result == {'is_new': True, 'user': mock_strategy.create_user.return_value}
