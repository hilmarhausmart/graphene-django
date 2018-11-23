from graphene.types.mutation import Mutation
from graphene.relay.mutation import ClientIDMutation

from .fields import DjangoField

# class DjangoMutation(Mutation):
#     pass

class DjangoClientIDMutation(ClientIDMutation):
    class Meta:
        abstract = True


    @classmethod
    def mutate(cls, root, info, input):
        return super(DjangoClientIDMutation, cls).mutate(root, info, input)

    @classmethod
    def Field(
        cls, name=None, description=None, deprecation_reason=None, required=False, permission_classes=None,
    ):
        return DjangoField(
            cls._meta.output,
            args=cls._meta.arguments,
            resolver=cls._meta.resolver,
            name=name,
            description=description,
            deprecation_reason=deprecation_reason,
            required=required,
            permission_classes=permission_classes,
        )
