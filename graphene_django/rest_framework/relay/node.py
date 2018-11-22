from graphene.relay import node as graphene_node

class NodeField(graphene_node.NodeField):
    def __init__(self, permission_classes=None, *args, **kwargs):
        super(NodeField, self).__init__(*args, **kwargs)

        self.permission_classes = permission_classes

    def get_resolver(self, parent_resolver):
        return super(NodeField, self).get_resolver(parent_resolver)


class Node(graphene_node.Node):
    @classmethod
    def Field(cls, permission_classes=None, *args, **kwargs):  # noqa: N802
        return NodeField(cls, permission_classes=permission_classes, *args, **kwargs)
