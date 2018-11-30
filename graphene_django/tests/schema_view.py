import graphene
from graphene import ObjectType, Schema

from rest_framework import serializers
from rest_framework.permissions import IsAdminUser, IsAuthenticated

from .models import Pet
from ..rest_framework.mutation import SerializerCreateMutation
from ..rest_framework.decorators import resolver_permission_classes

class QueryRoot(ObjectType):

    thrower = graphene.String(required=True)
    request = graphene.String(required=True)
    test = graphene.String(who=graphene.String())
    permission = graphene.String()
    authentication = graphene.String()

    def resolve_thrower(self, info):
        raise Exception("Throws!")

    def resolve_request(self, info):
        return info.context.get('request').GET.get("q")

    def resolve_test(self, info, who=None):
        return "Hello %s" % (who or "World")

    @resolver_permission_classes([IsAuthenticated])
    def resolve_authentication(self, info):
        return "Is authenticated"

    @resolver_permission_classes([IsAdminUser])
    def resolve_permission(self, info):
        return "Permission granted"


class PetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pet
        fields = "__all__"


class PetMutation(SerializerCreateMutation):
    class Meta:
        serializer_class = PetSerializer


class MutationRoot(ObjectType):
    write_test = graphene.Field(QueryRoot)
    write_serializer = PetMutation.Field()

    def resolve_write_test(self, info):
        return QueryRoot()


schema = Schema(query=QueryRoot, mutation=MutationRoot)
