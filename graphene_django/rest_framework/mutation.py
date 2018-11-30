from collections import OrderedDict

from django.http import Http404

from rest_framework.fields import SkipField

import graphene
import graphene.relay

from graphene.types import Field, InputField
from graphene.types.mutation import MutationOptions
from graphene.types.objecttype import yank_fields_from_attrs
from graphene.utils.str_converters import to_camel_case

from ..registry import get_global_registry
from ..mutation import DjangoClientIDMutation
from .serializer_converter import convert_serializer_field
from .types import ErrorType

registry = get_global_registry()


class SerializerMutationOptions(MutationOptions):
    lookup_field = None
    model_class = None
    serializer_class = None
    node_class = graphene.relay.Node
    node_type = None
    model_operations = None


def fields_for_serializer(
    serializer, only_fields, exclude_fields, is_input=False, is_update=False
):
    fields = OrderedDict()

    for name, field in serializer.fields.items():
        is_not_in_only = only_fields and name not in only_fields
        is_excluded = (
            name
            in exclude_fields  # or
            # name in already_created_fields
        )

        if is_not_in_only or is_excluded:
            continue

        converted_field = convert_serializer_field(field, is_input=is_input)

        if converted_field:
            if is_update and is_input and name == "id":
                raise Exception(
                    "Invalid SerializerUpdateMutation, serializer_class can only have a read_only id field."
                )
            fields[name] = converted_field
    return fields


class SerializerBaseMutation(DjangoClientIDMutation):
    class Meta:
        abstract = True

    errors = graphene.List(
        ErrorType, description="May contain more than one error for same field."
    )

    @classmethod
    def __init_subclass_with_meta__(
        cls,
        lookup_field=None,
        serializer_class=None,
        model_class=None,
        node_class=None,
        only_fields=(),
        exclude_fields=(),
        is_update=False,
        **options
    ):

        if not serializer_class:
            raise Exception("serializer_class is required for SerializerMutation")

        serializer = serializer_class()
        if model_class is None:
            serializer_meta = getattr(serializer_class, "Meta", None)
            if serializer_meta:
                model_class = getattr(serializer_meta, "model", None)

        if node_class and not issubclass(node_class, graphene.relay.Node):
            raise Exception("node_class must be a subclass of relay.Node")

        if lookup_field is None and model_class:
            lookup_field = model_class._meta.pk.name

        input_fields = fields_for_serializer(
            serializer, only_fields, exclude_fields, is_input=True, is_update=is_update
        )
        output_fields = fields_for_serializer(
            serializer, only_fields, exclude_fields, is_input=False, is_update=is_update
        )

        if is_update:
            input_fields["id"] = graphene.ID(
                required=True, description="ID of the object to update."
            )

        _meta = SerializerMutationOptions(cls)
        _meta.lookup_field = lookup_field
        _meta.serializer_class = serializer_class
        _meta.model_class = model_class
        _meta.fields = yank_fields_from_attrs(output_fields, _as=Field)

        if node_class:
            _meta.node_class = node_class

        input_fields = yank_fields_from_attrs(input_fields, _as=InputField)
        super(SerializerBaseMutation, cls).__init_subclass_with_meta__(
            _meta=_meta, input_fields=input_fields, **options
        )

    @classmethod
    def get_instance(cls, root, info, **input):
        return None

    @classmethod
    def get_serializer_kwargs(cls, root, info, **input):
        lookup_field = cls._meta.lookup_field
        model_class = cls._meta.model_class

        if model_class:
            instance = cls.get_instance(root, info, **input)

            return {
                "instance": instance,
                "data": input,
                "context": {"request": info.context.get("request", None)},
            }

        return {
            "data": input,
            "context": {"request": info.context.get("request", None)},
        }

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        kwargs = cls.get_serializer_kwargs(root, info, **input)
        serializer = cls._meta.serializer_class(**kwargs)

        if serializer.is_valid():
            return cls.perform_mutate(serializer, info)
        else:
            errors = [
                ErrorType(field=to_camel_case(key), messages=value)
                for key, value in serializer.errors.items()
            ]

            return cls(errors=errors)

    @classmethod
    def perform_mutate(cls, serializer, info):
        obj = serializer.save()

        kwargs = {}
        for f, field in serializer.fields.items():
            if not field.write_only:
                try:
                    kwargs[f] = field.get_attribute(obj)
                except SkipField:
                    pass

        return cls(errors=None, **kwargs)


class SerializerCreateMutation(SerializerBaseMutation):
    class Meta:
        abstract = True

    @classmethod
    def __init_subclass_with_meta__(
        cls,
        lookup_field=None,
        serializer_class=None,
        model_class=None,
        node_class=None,
        only_fields=(),
        exclude_fields=(),
        **options
    ):
        super(SerializerCreateMutation, cls).__init_subclass_with_meta__(
            lookup_field=lookup_field,
            serializer_class=serializer_class,
            model_class=model_class,
            node_class=node_class,
            only_fields=only_fields,
            exclude_fields=exclude_fields,
            is_update=False,
            **options
        )


class SerializerUpdateMutation(SerializerBaseMutation):
    class Meta:
        abstract = True

    @classmethod
    def __init_subclass_with_meta__(
        cls,
        lookup_field=None,
        serializer_class=None,
        model_class=None,
        node_class=None,
        only_fields=(),
        exclude_fields=(),
        **options
    ):
        super(SerializerUpdateMutation, cls).__init_subclass_with_meta__(
            lookup_field=lookup_field,
            serializer_class=serializer_class,
            model_class=model_class,
            node_class=node_class,
            only_fields=only_fields,
            exclude_fields=exclude_fields,
            is_update=True,
            **options
        )

    @classmethod
    def get_instance(cls, root, info, **input):
        if not input.get("id"):
            raise Exception('Invalid update operation. Input parameter "id" required.')

        model_class = cls._meta.model_class
        node_class = cls._meta.node_class

        model_type = registry.get_type_for_model(model_class)
        instance = node_class.get_node_from_global_id(info, input.get("id"), model_type)

        if instance is None:
            raise Http404(
                "No %s matches the given query." % model_class._meta.object_name
            )

        # instance = get_object_or_404(
        #     model_class, **{lookup_field: input[lookup_field]}
        # )

        return instance
