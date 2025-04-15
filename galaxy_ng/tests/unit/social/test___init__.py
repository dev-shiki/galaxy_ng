import sys

# Add project root to path if needed
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "galaxy_ng.settings")
from django.conf import settingsimport pytest
import os
import sys
Okay, I need to write comprehensive pytest tests for the provided Galaxy NG social module. Let me start by understanding the code structure and the functions involved.

First, the module contains a class GalaxyNGOAuth2 which extends GithubOAuth2. The main methods here are do_auth, handle_v3_namespace, and some helper functions like get_github_user, get_github_access_token, etc. There are also some utility methods like validate_namespace_name and transform_namespace_name.

The goal is to test all these methods with high coverage. Since this is a Django app, I'll need to use Django's testing framework along with pytest. I'll need to mock external services like GitHub API calls because hitting real endpoints in tests is bad practice.

Starting with the do_auth method. It calls get_github_user and handles namespaces. To test this, I can mock the get_github_user response. Also, the Namespace and LegacyNamespace models will need to be mocked or use Django's test database. But since these are models, maybe using pytest-django's transactional fixtures would help.

The handle_v3_namespace method has several branches. I need to test scenarios where the namespace exists and the user is an owner, not an owner, doesn't exist, etc. Also, the generate_available_namespace_name function loops until a unique name is found. I should test that it appends numbers correctly.

The validate_namespace_name uses a regex and some checks. Edge cases here would be names that are too short, start with an underscore, or don't match the regex.

For the get_github_access_token and get_github_user methods, I can mock the requests.post and requests.get responses to simulate successful and failed API calls. Testing error conditions here is important, like invalid access tokens or network errors.

The auth_complete method uses get_github_access_token and do_auth. So mocking the code parameter and ensuring the flow works when code is present.

Fixtures will be needed for the social auth strategy and request objects. Maybe using pytest fixtures to create mock instances of these.

I should also consider the logged decorator. Since it uses logging, perhaps using a mock logger to check if the logs are emitted as expected.

Possible test cases:

1. Test do_auth with valid access token, creating new namespace and legacy namespace.
2. Test handle_v3_namespace when namespace exists and user is owner (returns existing).
3. Test handle_v3_namespace when namespace exists but user isn't owner, so creates a new one with a suffix.
4. Test validate_namespace_name with valid and invalid names.
5. Test generate_available_namespace_name when the base name is taken, ensuring it appends numbers.
6. Test get_github_access_token with successful and failed responses.
7. Test get_github_user with valid and invalid responses.
8. Test auth_complete with valid code, and maybe invalid code leading to errors.
9. Edge cases like empty email, invalid GitHub responses, etc.

For mocks, I'll use pytest-mock or the unittest.mock library. Since it's Django, maybe using mixer or factory_boy to create test models, but since the code uses models directly, mocking them with MagicMock might be better to avoid database hits.

Wait, but for models like Namespace, maybe using the Django test database and creating instances via the ORM would be better. But since the code uses get_or_create and other queries, perhaps using the transactional fixtures from pytest-django would help. But for some tests, mocking the database queries might be necessary to isolate the code.

Hmm, perhaps a combination. For example, in tests where the actual database interaction is needed (like testing the creation of namespaces), use the test database. But for methods that depend on external APIs, mock those requests.

Wait, but in the code, the handle_v3_namespace interacts with the database (Namespace.objects). So for those tests, maybe using the Django test database with transactions rolled back after each test. So using pytest-django's TestCase or the transactional fixtures.

Alternatively, using pytest fixtures to set up the database. For example, a fixture that creates a Namespace instance before a test.

But to cover all branches, I need to set up different scenarios. Let me outline the steps for each test.

Starting with the do_auth method. Let's say:

Test case 1: do_auth with a new user, no existing namespace. Should create both v3 and legacy namespaces.

Test case 2: existing namespace owned by user, so returns that.

Test case 3: existing namespace not owned, so creates a new one with a suffix.

For each of these, I need to mock the get_github_user to return a user data, and set up the necessary models.

But mocking the social_core strategy and backend might be needed. Since GalaxyNGOAuth2 is a backend, perhaps in the tests, we can create an instance of it and mock its dependencies.

Wait, but in the code, the do_auth is part of the backend class. So to test it, perhaps we can create an instance of GalaxyNGOAuth2, mock its dependencies (like strategy, session, etc.), and call do_auth with appropriate parameters.

Alternatively, using the pytest-social-auth plugin might help, but maybe that's complicating. Since the user hasn't mentioned it, perhaps better to proceed with standard mocking.

So, for the first test:

Arrange:

- Mock the get_github_user to return a user with login 'testuser', email 'test@example.com', id 123.

- Mock the strategy.authenticate to return a user instance (maybe a mock user).

- Ensure that when handle_v3_namespace is called, it returns a new namespace.

- Then, check that the LegacyNamespace is created and linked.

But to do this, I need to mock the handle_v3_namespace method? Or let it run and mock the database?

Hmm, perhaps for the first test, let's mock the database interactions. For example, mock Namespace.objects.get_or_create to return a new namespace. But that might not be necessary if we can set up the test database properly.

Alternatively, using the Django test framework's TestCase, but since the user wants pytest, perhaps using pytest-django's features.

Wait, the user specified to use pytest, so I should structure the tests using pytest, with fixtures.

So, in the test file, I'll need to import the necessary modules, set up fixtures for the social auth backend, mock the GitHub API responses, and set up the database.

Let me think about the structure of the test file.

The test file will be in galaxy_ng/tests/unit/social/test___init__.py.

First, imports:

from django.test import override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from galaxy_ng.app.models import Namespace
from galaxy_ng.app.api.v1.models import LegacyNamespace
from galaxy_ng.social import GalaxyNGOAuth2
from galaxy_ng.app.utils import rbac
import pytest
from unittest import mock
from unittest.mock import MagicMock, patch
from social_core.backends.github import GithubOAuth2
from social_django.strategy import DjangoStrategy
from social_django.storage import DjangoUserMixin

Wait, but the GalaxyNGOAuth2 is in the module being tested, so importing from galaxy_ng.social should work.

Wait, the module is __init__.py in the social directory, so the class is in galaxy_ng.social.GalaxyNGOAuth2.

So the imports would be:

from galaxy_ng.social import GalaxyNGOAuth2

Now, fixtures. For example, a fixture to create a mock strategy and request.

Maybe a fixture for the backend instance:

@pytest.fixture
def backend():
    return GalaxyNGOAuth2(strategy=MagicMock(), storage=MagicMock())

But the strategy needs to be properly mocked. Alternatively, using a real strategy but with mocks.

Alternatively, using the social_django's strategy and storage.

Hmm, perhaps the backend requires a strategy and storage. So in the fixture, we can create a mock strategy and storage.

Alternatively, use the DjangoStrategy and DjangoUserMixin.

But maybe for simplicity, just mock the necessary parts.

Another fixture for the user model.

Also, for the GitHub API mocks, using the requests_mock library would be helpful. But since the user didn't mention it, perhaps using the unittest.mock.patch to mock requests.post and requests.get.

Wait, the code uses requests.post and requests.get in get_g