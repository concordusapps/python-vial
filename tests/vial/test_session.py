# -*- coding: utf-8 -*-
from vial import Vial
import redis


class TestSession:

    def setup(self):
        self.connection = redis.StrictRedis()
        self.vial = Vial()

    def test_new(self):
        session = self.vial.Session()

        assert b'_created' in session._cache
        assert b'_accessed' in session._cache

    def test_new_save(self):
        session = self.vial.Session()

        assert session.is_new

        session.save()

        assert not session.is_new
        assert session.id is not None
        assert self.connection.exists(session._key)

    def test_new_mapping(self):
        session = self.vial.Session()

        assert len(session) == 2
        assert b'_created' in list(iter(session))
        assert b'_accessed' in list(iter(session))

    def test_fetch_mapping(self):
        session = self.vial.Session()
        session.save()

        session = self.vial.Session(session._key)

        assert len(session) == 2
        assert b'_created' in list(iter(session))
        assert b'_accessed' in list(iter(session))

    def test_new_add_after(self):
        session = self.vial.Session()
        session.save()

        session['one'] = 1
        session['two'] = 'two'
        session['three'] = 3.0

        assert len(session) == 5

        session.save()

        assert b'one' in self.connection.hkeys(session._key)
        assert b'two' in self.connection.hkeys(session._key)
        assert self.connection.hget(session._key, b'three') == b'3.0'
        assert self.connection.hget(session._key, b'two') == b'two'
        assert self.connection.hget(session._key, b'one') == b'1'

    def test_new_add_and_fetch(self):
        session = self.vial.Session()

        assert session.is_new

        session[b'two'] = b'two'
        session.save()

        session = self.vial.Session(session.id)

        assert not session.is_new
        assert session[b'two'] == 'two'

    def test_set_accessed_time(self):
        session = self.vial.Session()
        accessed = session['_accessed']
        session.save()

        session = self.vial.Session(session.id)

        assert accessed != session['_accessed']

    def test_expire_session(self):
        session = self.vial.Session()
        session.save()

        expires = self.connection.ttl(session._key)
        assert expires <= (60 * 60 * 24)

    def test_cache(self):
        session = self.vial.Session()
        session.save()

        self.connection.hset(session._key, b'color', b'blue')

        assert session['color'] == 'blue'

        self.connection.hset(session._key, b'color', b'red')

        assert session['color'] == 'blue'

    def test_expunge(self):
        session = self.vial.Session()
        session.save()

        self.connection.hset(session._key, b'color', b'blue')

        assert session['color'] == 'blue'

        self.connection.hset(session._key, b'color', b'red')

        session.expunge()
        assert session['color'] == 'red'

    def test_no_expire(self):
        session = self.vial.Session(expires=False)
        session.save()

        expires = self.connection.ttl(session._key)
        assert expires == -1

    def test_remove_value(self):
        session = self.vial.Session()
        session.save()

        session['color'] = 'blue'
        session.save()

        assert self.connection.hget(session._key, b'color') == b'blue'

        session['color'] = None
        session.save()

        assert self.connection.hget(session._key, b'color') is None

    def test_del_value(self):
        session = self.vial.Session()
        session.save()

        session['color'] = 'blue'
        session.save()

        assert self.connection.hget(session._key, b'color') == b'blue'

        del session['color']
        session.save()

        assert self.connection.hget(session._key, b'color') is None

    def test_namespaced_key(self):
        session = self.vial.Session(namespace='vial')
        session.save()

        assert session._key.startswith(b'vial:')


class TestUserSession:

    def setup(self):
        self.connection = redis.StrictRedis()
        self.vial = Vial()

    def test_store_and_fetch_user(self):
        session = self.vial.UserSession()
        session.user = '12345'
        session.save()

        session = self.vial.UserSession(id=session.id)

        assert session.get('_user_id') == '12345'

    def test_expire_no_user_session(self):
        session = self.vial.UserSession()
        session.save()

        expires = self.connection.ttl(session._key)
        assert expires <= (60 * 60 * 24)

    def test_expire_user_session(self):
        session = self.vial.UserSession()
        session.user = '12345'
        session.save()

        expires = self.connection.ttl(session._key)
        assert expires <= (60 * 60 * 24 * 7)

    def test_get_all_by_user(self):
        session1 = self.vial.UserSession()
        session1.user = '12345'
        session1.save()

        session2 = self.vial.UserSession()
        session2.user = '12345'
        session2.save()

        sessions = list(self.vial.get_for_user('12345'))

        assert session1.id in sessions
        assert session2.id in sessions

    def test_delete_all_by_user(self):
        session1 = self.vial.UserSession()
        session1.user = '12345'
        session1.save()

        session2 = self.vial.UserSession()
        session2.user = '12345'
        session2.save()

        self.vial.delete_for_user('12345')

        assert self.vial.UserSession(id=session1.id).is_new
        assert self.vial.UserSession(id=session2.id).is_new
