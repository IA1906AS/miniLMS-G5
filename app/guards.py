"""Restrict routes to explicitly permitted roles."""

from collections.abc import Callable
from functools import wraps

from flask import g

from app.errors import Forbidden, UnauthenticatedError


def require_role[**P, R](
    *roles: str,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Reject unauthenticated actors and roles outside the allowlist."""
    allowed_roles = frozenset(roles)

    def decorate(view: Callable[P, R]) -> Callable[P, R]:
        @wraps(view)
        def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
            actor = g.get("actor")
            if actor is None:
                raise UnauthenticatedError()

            if actor.get("role") not in allowed_roles:
                raise Forbidden()

            return view(*args, **kwargs)

        return wrapped

    return decorate
