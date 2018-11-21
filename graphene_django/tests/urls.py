from django.conf.urls import url

from ..rest_framework.views import GraphQLAPIView
from ..views import GraphQLView


urlpatterns = [
    url(r"^graphql/batch", GraphQLView.as_view(batch=True)),
    url(r"^graphql", GraphQLView.as_view(graphiql=True)),

    url(r"^rest_framework/graphql/batch", GraphQLAPIView.as_view(graphene_batch=True)),
    url(r"^rest_framework/graphql", GraphQLAPIView.as_view(graphiql=True)),
]
