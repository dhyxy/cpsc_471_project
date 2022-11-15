import functools
import sqlite3
from typing import Callable, Optional, ParamSpec, TypeVar

from flask import current_app, g, redirect, url_for


def login_required(view):
    """Decorator to restrict a view to be for logged in users only."""

    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for("core.login"))
        return view(**kwargs)

    return wrapped_view

T = TypeVar('T')
P = ParamSpec('P')

def tries_to_commit(committing_func: Callable[P, T]) -> Callable[P, Optional[T]]:
    """Decorator to attempt to commit a SQLite command and handle potential error."""

    @functools.wraps(committing_func)
    def wrapped_commit(*args: P.args, **kwargs: P.kwargs):
        try:
            return committing_func(*args, **kwargs)
        except sqlite3.Error as e:
            current_app.logger.error(e)
            return None
    return wrapped_commit
