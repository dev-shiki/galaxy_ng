import pytest
from unittest.mock import patch, MagicMock
from django.contrib.auth import get_user_model
from galaxy_ng.app.utils.galaxy import generate_unverified_email
from galaxy_ng.social.pipeline.user import get_username, create_user

User = get_user_model()

@pytest.fixture
def mock_strategy():
    return MagicMock()

@pytest.fixture
def mock_details():
    return {
        'username': 'testuser',
        'email': 'testuser@example.com',
        'id': '12345'
    }

@pytest.fixture
def mock_backend():
    backend = MagicMock()
    backend.setting.return_value = ['username', 'email']
    return backend

@pytest.fixture
def mock_user():
    return User.objects.create(username='testuser', email='testuser@example.com')

@pytest.fixture
def mock_response():
    return {'id': '12345'}

def test_get_username(mock_strategy, mock_details, mock_backend):
    result = get_username(mock_strategy, mock_details, mock_backend)
    assert result == {'username': 'testuser'}

@patch('galaxy_ng.social.pipeline.user.logger.info')
def test_create_user_existing_user_same_username(mock_logger, mock_strategy, mock_details, mock_backend, mock_user):
    result = create_user(mock_strategy, mock_details, mock_backend, user=mock_user)
    mock_logger.assert_called_with('create_user(1): user-kwarg:testuser:1')
    assert result == {'is_new': False}

@patch('galaxy_ng.social.pipeline.user.logger.info')
def test_create_user_existing_user_different_username(mock_logger, mock_strategy, mock_details, mock_backend, mock_user):
    mock_details['username'] = 'newusername'
    result = create_user(mock_strategy, mock_details, mock_backend, user=mock_user)
    mock_logger.assert_called_with('create_user(6): set found user testuser:1 username to newusername')
    assert result == {'is_new': False}
    assert mock_user.username == 'newusername'

@patch('galaxy_ng.social.pipeline.user.logger.info')
def test_create_user_no_user_found_by_email(mock_logger, mock_strategy, mock_details, mock_backend):
    mock_details['email'] = 'newemail@example.com'
    result = create_user(mock_strategy, mock_details, mock_backend)
    mock_logger.assert_called_with('create_user(9): did not find any users via matching emails [\'user-12345\', \'newemail@example.com\']')
    assert result['is_new'] is True
    assert result['user'].email == 'newemail@example.com'

@patch('galaxy_ng.social.pipeline.user.logger.info')
def test_create_user_user_found_by_email(mock_logger, mock_strategy, mock_details, mock_backend, mock_user):
    result = create_user(mock_strategy, mock_details, mock_backend)
    mock_logger.assert_called_with('create_user(5): found user testuser:1 via email testuser@example.com')
    assert result == {'is_new': False, 'user': mock_user}

@patch('galaxy_ng.social.pipeline.user.logger.info')
def test_create_user_user_found_by_username(mock_logger, mock_strategy, mock_details, mock_backend, mock_user):
    mock_details['email'] = 'newemail@example.com'
    User.objects.create(username='testuser', email='differentemail@example.com')
    result = create_user(mock_strategy, mock_details, mock_backend)
    mock_logger.assert_called_with('create_user(10): found user:testuser:2:differentemail@example.com by username:testuser')
    assert result == {'is_new': False, 'user': mock_user}

@patch('galaxy_ng.social.pipeline.user.logger.info')
def test_create_user_user_found_by_username_with_no_email(mock_logger, mock_strategy, mock_details, mock_backend):
    mock_details['email'] = ''
    User.objects.create(username='testuser', email='')
    result = create_user(mock_strategy, mock_details, mock_backend)
    mock_logger.assert_called_with('create_user(10): found user:testuser:1: by username:testuser')
    assert result == {'is_new': False, 'user': User.objects.get(username='testuser')}

@patch('galaxy_ng.social.pipeline.user.logger.info')
def test_create_user_user_found_by_username_and_email_changed(mock_logger, mock_strategy, mock_details, mock_backend, mock_user):
    mock_details['email'] = 'newemail@example.com'
    User.objects.create(username='testuser', email='differentemail@example.com')
    result = create_user(mock_strategy, mock_details, mock_backend)
    mock_logger.assert_called_with('create_user(7): set found user testuser:2 email to newemail@example.com')
    assert result == {'is_new': False, 'user': User.objects.get(username='testuser', email='newemail@example.com')}

@patch('galaxy_ng.social.pipeline.user.logger.info')
def test_create_user_no_user_found_by_username_or_email(mock_logger, mock_strategy, mock_details, mock_backend):
    mock_details['username'] = 'newusername'
    mock_details['email'] = 'newemail@example.com'
    result = create_user(mock_strategy, mock_details, mock_backend)
    mock_logger.assert_called_with('create_user(13): newusername')
    assert result['is_new'] is True
    assert result['user'].username == 'newusername'
    assert result['user'].email == 'newemail@example.com'

@patch('galaxy_ng.social.pipeline.user.logger.info')
def test_create_user_no_fields(mock_logger, mock_strategy, mock_details, mock_backend):
    mock_backend.setting.return_value = []
    result = create_user(mock_strategy, mock_details, mock_backend)
    mock_logger.assert_called_with('create_user(3): no fields for None:None')
    assert result is None

@patch('galaxy_ng.social.pipeline.user.logger.info')
def test_create_user_no_github_id_in_details(mock_logger, mock_strategy, mock_details, mock_backend, mock_response):
    del mock_details['id']
    result = create_user(mock_strategy, mock_details, mock_backend, response=mock_response)
    mock_logger.assert_called_with('create_user(4): enumerate username:testuser email:testuser@example.com github_id:12345')
    assert result['is_new'] is True
    assert result['user'].username == 'testuser'
    assert result['user'].email == 'testuser@example.com'

@patch('galaxy_ng.social.pipeline.user.logger.info')
def test_create_user_no_email_in_details(mock_logger, mock_strategy, mock_details, mock_backend):
    del mock_details['email']
    result = create_user(mock_strategy, mock_details, mock_backend)
    mock_logger.assert_called_with('create_user(4): enumerate username:testuser email:None github_id:12345')
    assert result['is_new'] is True
    assert result['user'].username == 'testuser'
    assert result['user'].email == generate_unverified_email('12345')

@patch('galaxy_ng.social.pipeline.user.logger.info')
def test_create_user_no_username_in_details(mock_logger, mock_strategy, mock_details, mock_backend):
    del mock_details['username']
    result = create_user(mock_strategy, mock_details, mock_backend)
    mock_logger.assert_called_with('create_user(3): no fields for None:None')
    assert result is None

@patch('galaxy_ng.social.pipeline.user.logger.info')
def test_create_user_user_found_by_email_with_null_email(mock_logger, mock_strategy, mock_details, mock_backend):
    mock_details['email'] = None
    User.objects.create(username='testuser', email=generate_unverified_email('12345'))
    result = create_user(mock_strategy, mock_details, mock_backend)
    mock_logger.assert_called_with('create_user(5): found user testuser:1 via email user-12345')
    assert result == {'is_new': False, 'user': User.objects.get(username='testuser', email=generate_unverified_email('12345'))}

@patch('galaxy_ng.social.pipeline.user.logger.info')
def test_create_user_user_found_by_username_and_email_changed_to_null(mock_logger, mock_strategy, mock_details, mock_backend, mock_user):
    mock_details['email'] = None
    result = create_user(mock_strategy, mock_details, mock_backend)
    mock_logger.assert_called_with('create_user(7): set found user testuser:1 email to None')
    assert result == {'is_new': False, 'user': User.objects.get(username='testuser', email=None)}

@patch('galaxy_ng.social.pipeline.user.logger.info')
def test_create_user_user_found_by_username_and_email_changed_to_empty_string(mock_logger, mock_strategy, mock_details, mock_backend, mock_user):
    mock_details['email'] = ''
    result = create_user(mock_strategy, mock_details, mock_backend)
    mock_logger.assert_called_with('create_user(7): set found user testuser:1 email to ')
    assert result == {'is_new': False, 'user': User.objects.get(username='testuser', email='')}

@patch('galaxy_ng.social.pipeline.user.logger.info')
def test_create_user_user_found_by_username_and_email_changed_to_same(mock_logger, mock_strategy, mock_details, mock_backend, mock_user):
    result = create_user(mock_strategy, mock_details, mock_backend)
    mock_logger.assert_called_with('create_user(5): found user testuser:1 via email testuser@example.com')
    assert result == {'is_new': False, 'user': User.objects.get(username='testuser', email='testuser@example.com')}
