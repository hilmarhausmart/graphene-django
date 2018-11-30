import datetime

from graphene import Schema, Field, ResolveInfo, ObjectType
from graphene.types.inputobjecttype import InputObjectType
from py.test import raises
from py.test import mark
from rest_framework import serializers

from .conftest import (
    CreateMyModelMutation,
    UpdateMyModelMutation,
    MyModelSerializer,
    MyFakeModelType,
)
from .. import relay
from ...registry import reset_global_registry
from ...types import DjangoObjectType
from ..models import MyFakeModel
from ..mutation import SerializerCreateMutation, SerializerUpdateMutation



class MySerializer(serializers.Serializer):
    text = serializers.CharField()
    read = serializers.CharField(read_only=True)
    write = serializers.CharField(write_only=True)

    model = MyModelSerializer()

    def create(self, validated_data):
        return validated_data


def test_create_needs_serializer_class():
    with raises(Exception) as exc:

        class MyMutation(SerializerCreateMutation):
            pass

    assert str(exc.value) == "serializer_class is required for SerializerMutation"


def test_update_needs_serializer_class():
    with raises(Exception) as exc:

        class MyMutation(SerializerUpdateMutation):
            pass

    assert str(exc.value) == "serializer_class is required for SerializerMutation"


def test_create_has_fields():
    class MyMutation(SerializerCreateMutation):
        class Meta:
            serializer_class = MySerializer

    assert "id" not in MyMutation._meta.fields
    assert "text" in MyMutation._meta.fields
    assert "model" in MyMutation._meta.fields
    assert "errors" in MyMutation._meta.fields
    assert "read" in MyMutation._meta.fields
    assert "write" not in MyMutation._meta.fields


def test_update_create_has_fields():
    class MyMutation(SerializerCreateMutation):
        class Meta:
            serializer_class = MySerializer

    assert "id" not in MyMutation._meta.fields
    assert "text" in MyMutation._meta.fields
    assert "model" in MyMutation._meta.fields
    assert "errors" in MyMutation._meta.fields
    assert "read" in MyMutation._meta.fields
    assert "write" not in MyMutation._meta.fields


def test_create_has_input_fields():
    class MyMutation(SerializerCreateMutation):
        class Meta:
            serializer_class = MySerializer

    assert "id" not in MyMutation.Input._meta.fields
    assert "text" in MyMutation.Input._meta.fields
    assert "model" in MyMutation.Input._meta.fields
    assert "write" in MyMutation.Input._meta.fields
    assert "read" not in MyMutation.Input._meta.fields


def test_update_has_input_fields():
    class MyMutation(SerializerUpdateMutation):
        class Meta:
            serializer_class = MySerializer

    assert "id" in MyMutation.Input._meta.fields
    assert "text" in MyMutation.Input._meta.fields
    assert "model" in MyMutation.Input._meta.fields
    assert "write" in MyMutation.Input._meta.fields
    assert "read" not in MyMutation.Input._meta.fields


def test_exclude_fields():
    class MyMutation(SerializerCreateMutation):
        class Meta:
            serializer_class = MyModelSerializer
            exclude_fields = ["created"]

    assert "cool_name" in MyMutation._meta.fields
    assert "created" not in MyMutation._meta.fields
    assert "errors" in MyMutation._meta.fields
    assert "write_model" not in MyMutation._meta.fields
    assert "cool_name" in MyMutation.Input._meta.fields
    assert "created" not in MyMutation.Input._meta.fields
    assert "write_model" in MyMutation.Input._meta.fields


def test_update_with_writeable_id_error():
    class MyModelWriteIdSerializer(MyModelSerializer):
        id = serializers.IntegerField()

    with raises(Exception) as exc:

        class MyMutation(SerializerUpdateMutation):
            class Meta:
                serializer_class = MyModelWriteIdSerializer

    assert "can only have a read_only id field." in str(exc.value)


def test_nested_model():
    reset_global_registry()
    class MyFakeModelGrapheneType(DjangoObjectType):
        class Meta:
            model = MyFakeModel

    class MyMutation(SerializerCreateMutation):
        class Meta:
            serializer_class = MySerializer

    model_field = MyMutation._meta.fields["model"]
    assert isinstance(model_field, Field)
    assert model_field.type == MyFakeModelGrapheneType

    assert "created" in model_field._type._meta.fields
    assert "write_model" not in model_field._type._meta.fields

    model_input = MyMutation.Input._meta.fields["model"]
    model_input_type = model_input._type.of_type
    assert issubclass(model_input_type, InputObjectType)
    assert "cool_name" in model_input_type._meta.fields
    assert "created" not in model_input_type._meta.fields
    assert "write_model" in model_input_type._meta.fields


def test_mutate_and_get_payload_success(mock_info):
    class MyMutation(SerializerCreateMutation):
        class Meta:
            serializer_class = MySerializer

    result = MyMutation.mutate_and_get_payload(
        None,
        mock_info,
        **{
            "text": "value",
            "write": "write",
            "model": {"cool_name": "other_value", "write_model": "write_value"},
        }
    )
    assert result.errors is None


@mark.django_db
def test_model_add_mutate_and_get_payload_success(mock_info):
    result = CreateMyModelMutation.mutate_and_get_payload(
        None, mock_info, **{"cool_name": "Narf", "write_model": "Write Only"}
    )
    assert result.errors is None
    assert result.cool_name == "Narf"
    assert isinstance(result.created, datetime.datetime)


@mark.django_db
def test_model_update_mutate_and_get_payload_success(mock_info):
    instance = MyFakeModel.objects.create(cool_name="Narf")

    result = UpdateMyModelMutation.mutate_and_get_payload(
        None,
        mock_info,
        **{
            "id": "TXlGYWtlTW9kZWxUeXBlOjE=",
            "cool_name": "New Narf",
            "write_model": "Write Only",
        }
    )
    assert result.errors is None
    assert result.cool_name == "New Narf"

    instance.refresh_from_db()
    assert instance.cool_name == "New Narf"


@mark.django_db
def test_model_invalid_update_mutate_and_get_payload_success(mock_info):
    with raises(Exception) as exc:
        result = UpdateMyModelMutation.mutate_and_get_payload(
            None, mock_info, **{"cool_name": "Narf"}
        )

    assert '"id" required' in str(exc.value)


def test_mutate_and_get_payload_error(mock_info):
    class MyMutation(SerializerCreateMutation):
        class Meta:
            serializer_class = MySerializer

    # missing required fields
    result = MyMutation.mutate_and_get_payload(None, mock_info, **{})
    assert len(result.errors) == 3
    assert result.errors[0].field == "text"
    assert str(result.errors[0].messages[0]) == "This field is required."


def test_model_mutate_and_get_payload_error(mock_info):
    # missing required fields
    result = CreateMyModelMutation.mutate_and_get_payload(None, mock_info, **{})
    assert len(result.errors) > 0
    assert result.errors[0].field == "writeModel"
