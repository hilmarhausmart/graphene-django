import warnings

from graphene.types.mutation import Mutation
from graphene.relay.mutation import ClientIDMutation

from rest_framework.exceptions import PermissionDenied

from .fields import DjangoField

# class DjangoMutation(Mutation):
#     pass

class DjangoClientIDMutation(ClientIDMutation):
    class Meta:
        abstract = True


    @classmethod
    def mutate(cls, root, info, input, permission_classes=None):
        if not permission_classes:
            if hasattr(info, "context") and info.context and info.context.get("view", None):
                permission_classes = info.context.get(
                    "view"
                ).resolver_permission_classes
            else:
                warnings.warn(
                    UserWarning(
                        "DjangoNodeField should not be called without context."
                    )
                )

        if permission_classes:
            for permission in [p() for p in permission_classes]:
                if not permission.has_permission(
                    info.context.get("request"), info.context.get("view")
                ):
                    raise PermissionDenied(detail=getattr(permission, "message", None))


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
