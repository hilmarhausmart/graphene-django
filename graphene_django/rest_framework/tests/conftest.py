import pytest

from graphene import Schema, ResolveInfo, ObjectType

from rest_framework import serializers
from rest_framework.test import APIClient

from .. import relay
from ..models import MyFakeModel
from ..mutation import SerializerCreateMutation, SerializerUpdateMutation
from ...types import DjangoObjectType


@pytest.fixture
def api_client():
    return APIClient()


class MyFakeModelType(DjangoObjectType):
    class Meta:
        model = MyFakeModel
        interfaces = (relay.DjangoNode,)

    # @classmethod
    # def get_node(cls, info, id):
    #     try:
    #         return cls._meta.model.objects.get(pk=id)
    #     except cls._meta.model.DoesNotExist:
    #         return None


class MyModelSerializer(serializers.ModelSerializer):
    write_model = serializers.CharField(write_only=True)

    def create(self, validated_data):
        validated_data.pop("write_model")
        return super(MyModelSerializer, self).create(validated_data)

    class Meta:
        model = MyFakeModel
        fields = "__all__"
        read_only_fields = ("created",)


class CreateMyModelMutation(SerializerCreateMutation):
    class Meta:
        serializer_class = MyModelSerializer
        node_class = relay.DjangoNode


class UpdateMyModelMutation(SerializerUpdateMutation):
    class Meta:
        serializer_class = MyModelSerializer
        node_class = relay.DjangoNode


@pytest.fixture
def mock_info():
    class Mutation(ObjectType):
        create_my_model = CreateMyModelMutation.Field()
        update_my_model = UpdateMyModelMutation.Field()

    return ResolveInfo(
        None,
        None,
        None,
        None,
        schema=Schema(query=None, mutation=Mutation, types=[MyFakeModelType]),
        fragments=None,
        root_value=None,
        operation=None,
        variable_values=None,
        context={"request": None},
    )
