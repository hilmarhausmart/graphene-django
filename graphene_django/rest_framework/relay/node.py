import warnings

from functools import partial

from graphene.types.utils import get_type
from graphene.relay import node as graphene_node

from rest_framework.exceptions import PermissionDenied


class DjangoNodeField(graphene_node.NodeField):
    def __init__(self, *args, **kwargs):
        self.permission_classes = kwargs.pop("permission_classes", None)

        super(DjangoNodeField, self).__init__(*args, **kwargs)

    def get_resolver(self, parent_resolver):
        return partial(
            self.node_type.node_resolver,
            get_type(self.field_type),
            self.permission_classes,
        )


class DjangoNode(graphene_node.Node):
    @classmethod
    def Field(cls, *args, **kwargs):  # noqa: N802
        return DjangoNodeField(cls, *args, **kwargs)

    @classmethod
    def node_resolver(cls, only_type, permission_classes, root, info, id):
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

        return super(DjangoNode, cls).node_resolver(only_type, root, info, id)
