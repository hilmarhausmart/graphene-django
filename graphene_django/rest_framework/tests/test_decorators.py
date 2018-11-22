import pytest

from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied

from ..decorators import resolver_permission_classes

from .test_views import url_string, response_json


class user(object):
    is_authenticated = True


class anon(object):
    is_authenticated = False


class request(object):
    def __init__(self, user=None):
        self.user = user


class info(object):
    def __init__(self, user=None):
        self.context = {"request": request(user), "view": None}


def test_resolver_permission_classes_decorator():
    @resolver_permission_classes([])
    def no_permission(info):
        return True

    @resolver_permission_classes([AllowAny])
    def allow_any(info):
        return True

    @resolver_permission_classes([IsAuthenticated])
    def is_authenticated(info):
        return True

    assert no_permission(info()) == True
    assert allow_any(info()) == True
    assert is_authenticated(info(user=user())) == True

    with pytest.raises(PermissionDenied):
        is_authenticated(info(user=anon()))


@pytest.mark.django_db
def test_resolver_permission_classes_without_login(api_client, django_user_model):
    response = api_client.get(url_string(query="{authentication}"))

    assert response.status_code == 200
    assert response_json(response) == {
        "errors": [
            {
                "locations": [{"column": 2, "line": 1}],
                "message": "You do not have permission to perform this action.",
                "path": ["authentication"],
            }
        ],
        "data": {"authentication": None},
    }


@pytest.mark.django_db
def test_resolver_permission_classes_with_login(api_client, django_user_model):
    user = django_user_model.objects.create_user(username="foo", password="bar")

    api_client.force_authenticate(user=user)

    response = api_client.get(url_string(query="{authentication}"))

    assert response.status_code == 200
    assert response_json(response) == {"data": {"authentication": "Is authenticated"}}

    api_client.force_authenticate(user=None)


@pytest.mark.django_db
def test_resolver_permission_classes_without_permission(api_client, django_user_model):
    user = django_user_model.objects.create_user(username="foo", password="bar")

    api_client.force_authenticate(user=user)

    response = api_client.get(url_string(query="{permission}"))

    assert response.status_code == 200
    assert response_json(response) == {
        "errors": [
            {
                "locations": [{"column": 2, "line": 1}],
                "message": "You do not have permission to perform this action.",
                "path": ["permission"],
            }
        ],
        "data": {"permission": None},
    }

    api_client.force_authenticate(user=None)


@pytest.mark.django_db
def test_resolver_permission_classes_with_permission(api_client, django_user_model):
    superuser = django_user_model.objects.create_superuser(
        username="superfoo", password="superbar", email="foo@bar.com", is_staff=True
    )

    api_client.force_authenticate(user=superuser)

    response = api_client.get(url_string(query="{permission}"))

    assert response.status_code == 200
    assert response_json(response) == {"data": {"permission": "Permission granted"}}

    api_client.force_authenticate(user=None)

