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
                 expires=timedelta(days=1),
                 key_length=256):
        """Initialize a session store backed by redis.

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
            self._key = self._build_session_key(id)

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
                self._key = self._build_session_key(self.id)

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

    def _build_key(self, name, id):
        if self._namespace:
            return '%s:%s:%s' % (self._namespace, name, id)

        return '%s:%s' % (name, id)

    def _build_session_key(self, id):
        return self._build_key('session', id)

    def __getitem__(self, name):
        """Get a named value from the session."""
        # Ensure names are encoded as bytes for redis.
        if isinstance(name, str):
            name = name.encode('utf8')

        # Check the internal cache for the name.
        if name in self._cache:
            return self._cache[name]

        # Retrieve the name from redis.
        value = self._connection.hget(self._key, name)

        if value is not None:
            # Ensure values are strings.
            if isinstance(value, bytes):
                value = value.decode('utf8')

            # Store the value in the cache.
            self._cache[name] = value

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
