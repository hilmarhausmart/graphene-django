from functools import wraps

from rest_framework import exceptions


def context(f):
    def decorator(func):
        def wrapper(*args, **kwargs):
            info = args[f.__code__.co_varnames.index("info")]
            return func(info.context, *args, **kwargs)

        return wrapper

    return decorator


def resolver_permission_classes(permission_classes):
    def decorator(f):
        @wraps(f)
        @context(f)
        def wrapper(context, *args, **kwargs):
            for permission in [p() for p in permission_classes]:
                if not permission.has_permission(
                    context.get("request"), context.get("view")
                ):
                    raise exceptions.PermissionDenied(
                        detail=getattr(permission, "message", None)
                    )

            return f(*args, **kwargs)

        return wrapper

    return decorator

