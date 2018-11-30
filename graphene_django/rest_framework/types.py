from textwrap import dedent

import graphene

from graphene.types.unmountedtype import UnmountedType


class ErrorType(graphene.ObjectType):
    field = graphene.String(
        description=dedent(
            """Name of a field that caused the error. A value of
        `null` indicates that the error isn't associated with a particular
        field."""
        ),
        required=False,
    )
    messages = graphene.List(
        graphene.NonNull(graphene.String),
        description="The error messages.",
        required=True,
    )


class DictType(UnmountedType):
    key = graphene.String()
    value = graphene.String()
