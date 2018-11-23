import pytest
from rest_framework.test import APIClient


class _user(object):
    is_authenticated = True


class _anon(object):
    is_authenticated = False


class _request(object):
    def __init__(self, user=None):
        self.user = user


class _view(object):
    resolver_permission_classes = []

    def __init__(self, resolver_permission_classes=None):
        if resolver_permission_classes:
            self.resolver_permission_classes = resolver_permission_classes


class _info(object):
    def __init__(self, user=None, resolver_permission_classes=None):
        self.context = {
            "request": _request(user),
            "view": _view(resolver_permission_classes),
        }


@pytest.fixture
def info_with_context():
    return _info


@pytest.fixture
def info_with_context_anon():
    return _anon


@pytest.fixture
def info_with_context_user():
    return _user