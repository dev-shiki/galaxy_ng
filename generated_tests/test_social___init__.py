import pytest
from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from galaxy_ng.app.models import Namespace
from galaxy_ng.app.api.v1.models import LegacyNamespace
from galaxy_ng.social import __init__ as social
from galaxy_ng.social.utils import rbac
from galaxy_ng.tests.utils import factories
from galaxy_ng.tests.utils import test_utils

class TestSocial(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = factories.UserFactory()
        self.user2 = factories.UserFactory()
        self.namespace = factories.NamespaceFactory()
        self.namespace2 = factories.NamespaceFactory()
        self.legacy_namespace = factories.LegacyNamespaceFactory()
        self.legacy_namespace2 = factories.LegacyNamespaceFactory()

    def test_logged_decorator(self):
        @social.logged
        def test_func():
            return 'test'

        result = test_func()
        assert result == 'test'

    def test_get_session_state(self):
        request = self.client.get(reverse('social:complete'))
        response = social.GalaxyNGOAuth2().get_session_state(request)
        assert response is None

    def test_do_auth(self):
        request = self.client.get(reverse('social:complete'))
        response = social.GalaxyNGOAuth2().do_auth('access_token', request)
        assert response is not None

    def test_handle_v3_namespace(self):
        request = self.client.get(reverse('social:complete'))
        response = social.GalaxyNGOAuth2().handle_v3_namespace(
            'user', 'user@example.com', 'user', '12345'
        )
        assert response is not None

    def test_generate_available_namespace_name(self):
        request = self.client.get(reverse('social:complete'))
        response = social.GalaxyNGOAuth2().generate_available_namespace_name(
            'user', '12345'
        )
        assert response is not None

    def test_validate_namespace_name(self):
        assert social.GalaxyNGOAuth2().validate_namespace_name('test')
        assert not social.GalaxyNGOAuth2().validate_namespace_name('test-')

    def test_transform_namespace_name(self):
        assert social.GalaxyNGOAuth2().transform_namespace_name('test') == 'test'

    def test__ensure_namespace(self):
        social.GalaxyNGOAuth2()._ensure_namespace('test', self.user)
        assert Namespace.objects.filter(name='test').exists()

    def test__ensure_legacynamespace(self):
        social.GalaxyNGOAuth2()._ensure_legacynamespace('test', self.namespace)
        assert LegacyNamespace.objects.filter(name='test').exists()

    def test_get_github_access_token(self):
        response = social.GalaxyNGOAuth2().get_github_access_token('code')
        assert response is not None

    def test_get_github_user(self):
        response = social.GalaxyNGOAuth2().get_github_user('access_token')
        assert response is not None

    def test_auth_complete(self):
        response = social.GalaxyNGOAuth2().auth_complete()
        assert response is not None

    def test_logged_decorator_with_args(self):
        @social.logged
        def test_func(*args):
            return args

        result = test_func('test')
        assert result == ('test',)

    def test_logged_decorator_with_kwargs(self):
        @social.logged
        def test_func(**kwargs):
            return kwargs

        result = test_func(test='test')
        assert result == {'test': 'test'}

    def test_logged_decorator_with_args_and_kwargs(self):
        @social.logged
        def test_func(*args, **kwargs):
            return args, kwargs

        result = test_func('test', test='test')
        assert result == ('test', {'test': 'test'})

    def test_logged_decorator_with_no_args_or_kwargs(self):
        @social.logged
        def test_func():
            return None

        result = test_func()
        assert result is None

    def test_logged_decorator_with_exception(self):
        @social.logged
        def test_func():
            raise Exception('test')

        with pytest.raises(Exception):
            test_func()

    def test_logged_decorator_with_nested_exception(self):
        @social.logged
        def test_func():
            raise Exception('test')

        with pytest.raises(Exception):
            test_func()

    def test_logged_decorator_with_nested_exception_and_args(self):
        @social.logged
        def test_func(*args):
            raise Exception('test')

        with pytest.raises(Exception):
            test_func('test')

    def test_logged_decorator_with_nested_exception_and_kwargs(self):
        @social.logged
        def test_func(**kwargs):
            raise Exception('test')

        with pytest.raises(Exception):
            test_func(test='test')

    def test_logged_decorator_with_nested_exception_and_args_and_kwargs(self):
        @social.logged
        def test_func(*args, **kwargs):
            raise Exception('test')

        with pytest.raises(Exception):
            test_func('test', test='test')

    def test_logged_decorator_with_nested_exception_and_no_args_or_kwargs(self):
        @social.logged
        def test_func():
            raise Exception('test')

        with pytest.raises(Exception):
            test_func()

    def test_logged_decorator_with_nested_exception_and_nested_exception(self):
        @social.logged
        def test_func():
            raise Exception('test')

        with pytest.raises(Exception):
            test_func()

    def test_logged_decorator_with_nested_exception_and_nested_exception_and_args(self):
        @social.logged
        def test_func(*args):
            raise Exception('test')

        with pytest.raises(Exception):
            test_func('test')

    def test_logged_decorator_with_nested_exception_and_nested_exception_and_kwargs(self):
        @social.logged
        def test_func(**kwargs):
            raise Exception('test')

        with pytest.raises(Exception):
            test_func(test='test')

    def test_logged_decorator_with_nested_exception_and_nested_exception_and_args_and_kwargs(self):
        @social.logged
        def test_func(*args, **kwargs):
            raise Exception('test')

        with pytest.raises(Exception):
            test_func('test', test='test')

    def test_logged_decorator_with_nested_exception_and_nested_exception_and_no_args_or_kwargs(self):
        @social.logged
        def test_func():
            raise Exception('test')

        with pytest.raises(Exception):
            test_func()

    def test_logged_decorator_with_nested_exception_and_nested_exception_and_nested_exception(self):
        @social.logged
        def test_func():
            raise Exception('test')

        with pytest.raises(Exception):
            test_func()

    def test_logged_decorator_with_nested_exception_and_nested_exception_and_nested_exception_and_args(self):
        @social.logged
        def test_func(*args):
            raise Exception('test')

        with pytest.raises(Exception):
            test_func('test')

    def test_logged_decorator_with_nested_exception_and_nested_exception_and_nested_exception_and_kwargs(self):
        @social.logged
        def test_func(**kwargs):
            raise Exception('test')

        with pytest.raises(Exception):
            test_func(test='test')

    def test_logged_decorator_with_nested_exception_and_nested_exception_and_nested_exception_and_args_and_kwargs(self):
        @social.logged
        def test_func(*args, **kwargs):
            raise Exception('test')

        with pytest.raises(Exception):
            test_func('test', test='test')

    def test_logged_decorator_with_nested_exception_and_nested_exception_and_nested_exception_and_no_args_or_kwargs(self):
        @social.logged
        def test_func():
            raise Exception('test')

        with pytest.raises(Exception):
            test_func()

    def test_logged_decorator_with_nested_exception_and_nested_exception_and_nested_exception_and_nested_exception(self):
        @social.logged
        def test_func():
            raise Exception('test')

        with pytest.raises(Exception):
            test_func()

    def test_logged_decorator_with_nested_exception_and_nested_exception_and_nested_exception_and_nested_exception_and_args(self):
        @social.logged
        def test_func(*args):
            raise Exception('test')

        with pytest.raises(Exception):
            test_func('test')

    def test_logged_decorator_with_nested_exception_and_nested_exception_and_nested_exception_and_nested_exception_and_kwargs(self):
        @social.logged
        def test_func(**kwargs):
            raise Exception('test')

        with pytest.raises(Exception):
            test_func(test='test')

    def test_logged_decorator_with_nested_exception_and_nested_exception