import pytest

from datetime import datetime
from mock import patch

from graphene import Interface, ObjectType, Schema, Connection, String

from graphql.error.located_error import GraphQLLocatedError

from rest_framework.permissions import IsAuthenticated, IsAdminUser

from .. import relay
from ... import registry
from ...connection import DjangoConnection
from ...types import DjangoObjectType, DjangoObjectTypeOptions
from ...fields import DjangoConnectionField
from ...tests.models import Article as ArticleModel
from ...tests.models import Reporter as ReporterModel

registry.reset_global_registry()


class user(object):
    is_authenticated = True


class anon(object):
    is_authenticated = False


class request(object):
    def __init__(self, user=None):
        self.user = user


class view(object):
    resolver_permission_classes = []

    def __init__(self, resolver_permission_classes=None):
        if resolver_permission_classes:
            self.resolver_permission_classes = resolver_permission_classes


class info(object):
    def __init__(self, user=None, resolver_permission_classes=None):
        self.context = {
            "request": request(user),
            "view": view(resolver_permission_classes),
        }


class Reporter(DjangoObjectType):
    """Reporter description"""

    class Meta:
        model = ReporterModel


class ArticleConnection(DjangoConnection):
    """Article Connection"""

    test = String()

    def resolve_test():
        return "test"

    class Meta:
        abstract = True


class Article(DjangoObjectType):
    """Article description"""

    class Meta:
        model = ArticleModel
        interfaces = (relay.DjangoNode,)
        connection_class = ArticleConnection


class RootQuery(ObjectType):
    nodes = DjangoConnectionField(Article)
    permission_nodes = DjangoConnectionField(
        Article, permission_classes=[IsAuthenticated]
    )

    node = relay.DjangoNode.Field(Article)
    permission_node = relay.DjangoNode.Field(
        Article, permission_classes=[IsAuthenticated]
    )


schema = Schema(query=RootQuery)


@pytest.mark.django_db
def test_fields_should_not_require_permissions():
    r1 = ReporterModel.objects.create(
        first_name="r1", last_name="r1", email="r1@test.com"
    )
    r2 = ReporterModel.objects.create(
        first_name="r2", last_name="r2", email="r2@test.com"
    )
    ArticleModel.objects.create(
        headline="a1",
        pub_date=datetime.now(),
        pub_date_time=datetime.now(),
        reporter=r1,
        editor=r1,
    )
    ArticleModel.objects.create(
        headline="a2",
        pub_date=datetime.now(),
        pub_date_time=datetime.now(),
        reporter=r2,
        editor=r2,
    )

    query = """
        query {
            nodes {
                edges {
                    node {
                        id
                    }
                }
            }
        }
    """

    result = schema.execute(query)
    assert not result.errors
    assert result.data == {
        "nodes": {
            "edges": [
                {"node": {"id": "QXJ0aWNsZTox"}},
                {"node": {"id": "QXJ0aWNsZToy"}},
            ]
        }
    }


@pytest.mark.django_db
def test_fields_should_require_permissions():
    r1 = ReporterModel.objects.create(
        first_name="r1", last_name="r1", email="r1@test.com"
    )
    r2 = ReporterModel.objects.create(
        first_name="r2", last_name="r2", email="r2@test.com"
    )
    ArticleModel.objects.create(
        headline="a1",
        pub_date=datetime.now(),
        pub_date_time=datetime.now(),
        reporter=r1,
        editor=r1,
    )
    ArticleModel.objects.create(
        headline="a2",
        pub_date=datetime.now(),
        pub_date_time=datetime.now(),
        reporter=r2,
        editor=r2,
    )

    query = """
        query {
            permissionNodes {
                edges {
                    node {
                        id
                    }
                }
            }
        }
    """

    result = schema.execute(query, context=info().context)
    assert len(result.errors) == 1
    assert (
        result.errors[0].message == "You do not have permission to perform this action."
    )
    assert result.data == {"permissionNodes": None}


@pytest.mark.django_db
def test_fields_with_correct_permission():
    r1 = ReporterModel.objects.create(
        first_name="r1", last_name="r1", email="r1@test.com"
    )
    r2 = ReporterModel.objects.create(
        first_name="r2", last_name="r2", email="r2@test.com"
    )
    ArticleModel.objects.create(
        headline="a1",
        pub_date=datetime.now(),
        pub_date_time=datetime.now(),
        reporter=r1,
        editor=r1,
    )
    ArticleModel.objects.create(
        headline="a2",
        pub_date=datetime.now(),
        pub_date_time=datetime.now(),
        reporter=r2,
        editor=r2,
    )

    query = """
        query {
            permissionNodes {
                edges {
                    node {
                        id
                    }
                }
            }
        }
    """

    result = schema.execute(query, context=info(user=user()).context)
    assert not result.errors
    assert result.data == {
        "permissionNodes": {
            "edges": [
                {"node": {"id": "QXJ0aWNsZTox"}},
                {"node": {"id": "QXJ0aWNsZToy"}},
            ]
        }
    }


@pytest.mark.django_db
def test_relay_node_should_not_require_permissions():
    r1 = ReporterModel.objects.create(
        first_name="r1", last_name="r1", email="r1@test.com"
    )
    ArticleModel.objects.create(
        headline="a1",
        pub_date=datetime.now(),
        pub_date_time=datetime.now(),
        reporter=r1,
        editor=r1,
    )

    query = """
        query {
            node(id: "QXJ0aWNsZTox") {
                id
            }
        }
    """

    result = schema.execute(query, context=info().context)
    assert not result.errors
    assert result.data == {"node": {"id": "QXJ0aWNsZTox"}}


@pytest.mark.django_db
def test_relay_node_should_require_permissions():
    r1 = ReporterModel.objects.create(
        first_name="r1", last_name="r1", email="r1@test.com"
    )
    ArticleModel.objects.create(
        headline="a1",
        pub_date=datetime.now(),
        pub_date_time=datetime.now(),
        reporter=r1,
        editor=r1,
    )

    query = """
        query {
            permissionNode(id: "QXJ0aWNsZTox") {
                id
            }
        }
    """

    result = schema.execute(query, context=info(anon()).context)
    assert len(result.errors) == 1
    assert (
        result.errors[0].message == "You do not have permission to perform this action."
    )
    assert result.data == {"permissionNode": None}


@pytest.mark.django_db
def test_relay_node_with_permissions():
    r1 = ReporterModel.objects.create(
        first_name="r1", last_name="r1", email="r1@test.com"
    )
    ArticleModel.objects.create(
        headline="a1",
        pub_date=datetime.now(),
        pub_date_time=datetime.now(),
        reporter=r1,
        editor=r1,
    )

    query = """
        query {
            permissionNode(id: "QXJ0aWNsZTox") {
                id
            }
        }
    """

    result = schema.execute(query, context=info(user()).context)
    assert not result.errors
    assert result.data == {"permissionNode": {"id": "QXJ0aWNsZTox"}}


@pytest.mark.django_db
def test_relay_node_should_require_permissions_from_view():
    r1 = ReporterModel.objects.create(
        first_name="r1", last_name="r1", email="r1@test.com"
    )
    ArticleModel.objects.create(
        headline="a1",
        pub_date=datetime.now(),
        pub_date_time=datetime.now(),
        reporter=r1,
        editor=r1,
    )

    query = """
        query {
            node(id: "QXJ0aWNsZTox") {
                id
            }
        }
    """

    result = schema.execute(
        query,
        context=info(
            user=anon(), resolver_permission_classes=[IsAuthenticated]
        ).context,
    )
    assert len(result.errors) == 1
    assert (
        result.errors[0].message == "You do not have permission to perform this action."
    )
    assert result.data == {"node": None}



@pytest.mark.django_db
def test_relay_node_should_override_permissions_from_view():
    r1 = ReporterModel.objects.create(
        first_name="r1", last_name="r1", email="r1@test.com"
    )
    ArticleModel.objects.create(
        headline="a1",
        pub_date=datetime.now(),
        pub_date_time=datetime.now(),
        reporter=r1,
        editor=r1,
    )

    query = """
        query {
            permissionNode(id: "QXJ0aWNsZTox") {
                id
            }
        }
    """

    result = schema.execute(
        query,
        context=info(
            user=anon(), resolver_permission_classes=[IsAdminUser]
        ).context,
    )
    assert len(result.errors) == 1
    assert (
        result.errors[0].message == "You do not have permission to perform this action."
    )
    assert result.data == {"permissionNode": None}



@pytest.mark.django_db
def test_fields_should_require_permissions_from_view():
    r1 = ReporterModel.objects.create(
        first_name="r1", last_name="r1", email="r1@test.com"
    )
    r2 = ReporterModel.objects.create(
        first_name="r2", last_name="r2", email="r2@test.com"
    )
    ArticleModel.objects.create(
        headline="a1",
        pub_date=datetime.now(),
        pub_date_time=datetime.now(),
        reporter=r1,
        editor=r1,
    )
    ArticleModel.objects.create(
        headline="a2",
        pub_date=datetime.now(),
        pub_date_time=datetime.now(),
        reporter=r2,
        editor=r2,
    )

    query = """
        query {
            nodes {
                edges {
                    node {
                        id
                    }
                }
            }
        }
    """

    result = schema.execute(
        query,
        context=info(
            user=anon(), resolver_permission_classes=[IsAuthenticated]
        ).context,
    )
    assert len(result.errors) == 1
    assert (
        result.errors[0].message == "You do not have permission to perform this action."
    )
    assert result.data == {"nodes": None}



@pytest.mark.django_db
def test_fields_should_override_permissions_from_view():
    r1 = ReporterModel.objects.create(
        first_name="r1", last_name="r1", email="r1@test.com"
    )
    r2 = ReporterModel.objects.create(
        first_name="r2", last_name="r2", email="r2@test.com"
    )
    ArticleModel.objects.create(
        headline="a1",
        pub_date=datetime.now(),
        pub_date_time=datetime.now(),
        reporter=r1,
        editor=r1,
    )
    ArticleModel.objects.create(
        headline="a2",
        pub_date=datetime.now(),
        pub_date_time=datetime.now(),
        reporter=r2,
        editor=r2,
    )

    query = """
        query {
            permissionNodes {
                edges {
                    node {
                        id
                    }
                }
            }
        }
    """

    result = schema.execute(
        query,
        context=info(
            user=anon(), resolver_permission_classes=[IsAdminUser]
        ).context,
    )
    assert len(result.errors) == 1
    assert (
        result.errors[0].message == "You do not have permission to perform this action."
    )
    assert result.data == {"permissionNodes": None}
