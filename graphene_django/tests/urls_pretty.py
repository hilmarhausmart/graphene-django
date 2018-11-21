from django.conf.urls import url

from ..rest_framework.views import GraphQLAPIView
from ..views import GraphQLView
from .schema_view import schema

urlpatterns = [
    url(r"^graphql", GraphQLView.as_view(schema=schema, pretty=True)),
    url(
        r"^rest_framework/graphql",
        GraphQLAPIView.as_view(
            graphene_schema=schema, graphiql=True, graphene_pretty=True
        ),
    ),
]
