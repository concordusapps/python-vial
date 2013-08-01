# -*- coding: utf-8 -*-
import redis
import collections
import os
import time
from base64 import urlsafe_b64encode
from datetime import timedelta


class Session(collections.MutableMapping):

    def __init__(self, id=None,
                 host='localhost', port=6379, db=0, namespace=None,
                 connection=None,
                 expires=timedelta(days=1),
                 key_length=256):
        """Initialize a session object backed by redis.

        @param[in] key Optional session key to retrieve the session from.
        @param[in] host Hostname to access the redis server.
        @param[in] port Port on the host to access the redis server.
        @param[in] db Database index on redis to use.
        """
        #! Optional namespace to use (eg. 'vial') so keys are
        #! stored namespaced (eg. 'vial:session:<id>').
        self._namespace = namespace

        #! The internal key/value cache.
        self._cache = {}

        #! The connection to redis.
        self._connection = connection
        if connection is None:
            self._connection = redis.StrictRedis(host=host, port=port, db=db)

        #! Time length to set the sessions to expire at.
        #! Set to False to never have sessions expire.
        self._expires = expires

        #! Length of a generated session key.
        self._key_length = key_length

        #! The key of the session in redis.
        self._key = None

        #! The session identifer is None for new sessions.
        self.id = None

        self._new = True
        if id is not None:
            # Store the given session identifier.
            self.id = id

            # Build the redis format string for the session.
            self._key = self._build_session_key(self._namespace, id)

            # Check if the session already exists.
            self._new = not self._connection.exists(self._key)

        if self._new:
            # Set created time if neccessary.
            self['_created'] = time.time()

        else:
            # Refresh the session.
            self.refresh()

        # Update accessed time.
        self['_accessed'] = time.time()

    @property
    def is_new(self):
        return self._new

    def expunge(self):
        """Clear the internal key/value cache."""
        self._cache.clear()

    def refresh(self):
        """Refresh the session expiration time."""
        if self._expires:
            self._connection.expire(self._key, self._expires)

        else:
            self._connection.persist(self._key)

    def save(self):
        """Persist the session to redis."""
        if self._new:
            loop = True
            while loop:
                # Generate a new session identifier until it is actually new.
                self.id = urlsafe_b64encode(os.urandom(self._key_length))

                # Build the redis format string for the session.
                self._key = self._build_session_key(self._namespace, self.id)

                # Test if its new.
                loop = self._connection.exists(self._key)

            # We are no longer new.
            self._new = False

        # Remove all keys of the hash that have been set to null.
        keys = list(filter(lambda n: self._cache[n] is None, self._cache))
        if keys:
            self._connection.hdel(self._key, *keys)
            for key in keys:
                del self._cache[key]

        # Persist our remaining keys.
        self._connection.hmset(self._key, self._cache)

        # Refresh the session.
        self.refresh()

    @classmethod
    def _build_key(cls, namespace, name, id):
        if isinstance(id, bytes):
            id = id.decode('utf8')

        if namespace:
            key = '%s:%s:%s' % (namespace, name, id)

        else:
            key = '%s:%s' % (name, id)

        return key.encode('utf8')

    @classmethod
    def _build_session_key(cls, namespace, id):
        return cls._build_key(namespace, 'session', id)

    def __getitem__(self, name):
        """Get a named value from the session."""
        # Ensure names are encoded as bytes for redis.
        if isinstance(name, str):
            name = name.encode('utf8')

        # Check the internal cache for the name.
        if name in self._cache:
            value = self._cache[name]

        else:
            # Retrieve the name from redis.
            value = self._connection.hget(self._key, name)
            if value is None:
                raise KeyError

            # Store the value in the cache.
            self._cache[name] = value

        # Ensure values are strings.
        if isinstance(value, bytes):
            value = value.decode('utf8')

        # Return our value.
        return value

    def __setitem__(self, name, value):
        """Set a named value from the session."""
        # Ensure names are encoded as bytes for redis.
        if isinstance(name, str):
            name = name.encode('utf8')

        # Ensure values are encoded as bytes for redis.
        if isinstance(value, str):
            value = value.encode('utf8')

        # Store the value in the cache.
        self._cache[name] = value

    def __delitem__(self, name):
        """Remove a named value from the session."""
        # Ensure names are encoded as bytes for redis.
        if isinstance(name, str):
            name = name.encode('utf8')

        # Set the value to nothing (to signal removal).
        self._cache[name] = None

    def __len__(self):
        """Retrieves the number of named values stored in the session."""
        if self._key:
            # Pull everything into the cache.
            self.update(self._connection.hgetall(self._key))

        # Return the number of named values.
        return len(self._cache)

    def __iter__(self):
        """Iterates through every named value in the session."""
        if self._key:
            # Pull everything into the cache.
            self.update(self._connection.hgetall(self._key))

        # Return the number of named values.
        return iter(self._cache)


class UserSession(Session):

    def __init__(self, id=None, user=None, user_expires=timedelta(days=1),
                 **kwargs):
        """Initialize a user session object backed by redis."""
        #! Time length to set the sessions to expire at for users..
        #! Set to False to never have sessions expire for users.
        self._user_expires = user_expires

        # Initialize the base session object.
        super().__init__(id=id, **kwargs)

        #! The key of the user's session in redis.
        self._user_key = None

        # Set the user if we were given one.
        if user is not None:
            self.user = user

    @classmethod
    def _build_user_key(cls, namespace, id):
        return cls._build_key(namespace, 'user', id)

    @property
    def user(self):
        """Get the user identifier stored in the session."""
        return self.get('_user_id', None)

    @user.setter
    def user(self, value):
        """Set the user for the session."""
        old = self.user
        if not self.is_new and old:
            # Remove this session identifier from the previous user.
            key = self._build_user_key(self._namespace, old)
            self._connection.srem(key, self._key)

        # Build the user key.
        self._user_key = self._build_user_key(self._namespace, value)

        # Set the user identifier in the session.
        self['_user_id'] = value

    def save(self):
        # Persist the session object.
        super().save()

        if self._user_key:
            # Append this session identifier as a session for the user.
            self._connection.sadd(self._user_key, self._key)

    def refresh(self):
        """Refresh the session expiration time.

        The session expiration time is affected by whether this session
        is bound to a user or not.
        """
        if self.user is None:
            super().refresh()

        else:
            if self._user_expires:
                self._connection.expire(self._key, self._user_expires)

            else:
                self._connection.persist(self._key)
