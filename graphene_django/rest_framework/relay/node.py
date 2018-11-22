from functools import partial

from graphene.types.utils import get_type
from graphene.relay import node as graphene_node

from rest_framework.exceptions import PermissionDenied

class DjangoNodeField(graphene_node.NodeField):
    def __init__(self, *args, **kwargs):
        self.permission_classes = kwargs.pop('permission_classes', [])

        super(DjangoNodeField, self).__init__(*args, **kwargs)

    def get_resolver(self, parent_resolver):
        return partial(self.node_type.node_resolver, get_type(self.field_type), self.permission_classes)


class DjangoNode(graphene_node.Node):
    @classmethod
    def Field(cls, *args, **kwargs):  # noqa: N802
        return DjangoNodeField(cls, *args, **kwargs)

    @classmethod
    def node_resolver(cls, only_type, permission_classes, root, info, id):
        for permission in [p() for p in permission_classes]:
            if not permission.has_permission(
                info.context.get("request"), info.context.get("view")
            ):
                raise PermissionDenied(
                    detail=getattr(permission, "message", None)
                )

        return super(DjangoNode, cls).node_resolver(only_type, root, info, id)
