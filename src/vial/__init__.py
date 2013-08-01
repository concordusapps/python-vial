# -*- coding: utf-8 -*-
import sys
from .meta import version as __version__, description
from .session import Session, UserSession
import redis

# Set the package docstring to the metadata description.
sys.modules[__package__].__doc__ = description

# Expose named attributes.
__all__ = [
    'Vial',
    'Session',
    'UserSession'
]


class Vial:

    def __init__(self, host='localhost', port=6379, db=0, namespace=None):
        """Initialize a session store backed by redis.

        @param[in] key Optional session key to retrieve the session from.
        @param[in] host Hostname to access the redis server.
        @param[in] port Port on the host to access the redis server.
        @param[in] db Database index on redis to use.
        """
        #! Optional namespace to use (eg. 'vial') so keys are
        #! stored namespaced (eg. 'vial:session:<id>').
        self._namespace = namespace

        #! The connection to redis.
        self._connection = redis.StrictRedis(host=host, port=port, db=db)

    def Session(self, *args, **kwargs):
        kwargs.setdefault('namespace', self._namespace)
        kwargs['connection'] = self._connection
        return Session(*args, **kwargs)

    def UserSession(self, *args, **kwargs):
        kwargs.setdefault('namespace', self._namespace)
        kwargs['connection'] = self._connection
        return UserSession(*args, **kwargs)

    def get_for_user(self, user):
        """Retrieve all session ids bound to this user."""
        text = UserSession._build_user_key(self._namespace, user)
        members = self._connection.smembers(text)
        for key in members:
            yield key.split(b':', 2)[-1]

    def delete_for_user(self, user):
        """Delete all sessions bound to this user."""
        key = UserSession._build_user_key(self._namespace, user)
        members = self._connection.smembers(key)

        # Remove all sessions.
        if members:
            self._connection.delete(*members)

        # Remove the user session set.
        self._connection.delete(key)
