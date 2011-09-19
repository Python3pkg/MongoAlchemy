"""
Utilities used throughout the tests.

"""

from functools import wraps
from mongoalchemy.session import Session


DB_NAME = 'mongoalchemy-unit-test'
""" Name of the database to use for testing. """


def known_failure(fun):
    """
    Wraps a test known to fail without causing an actual test failure.

    """
    @wraps(fun)
    def wrapper(*args, **kwds):
        try:
            fun(*args, **kwds)
            raise Exception('Known failure passed! %s' % fun.__name__)
        except:
            pass
    return wrapper


def get_session(*args, **kwargs):
    """
    Returns the :class:`Session` used for testing.

    """
    return Session.connect(DB_NAME, *args, **kwargs)

