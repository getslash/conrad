import time

import pytest
from flask_app.views import get_redis_connection


def test_set(webapp, path, data, saved):
    assert webapp.get(str(path)) == {"result": data}


def test_get_raw(webapp, path, data, saved):
    assert webapp.get_raw(path + "?raw=true").content == data


def test_get_all(webapp, path, data):
    def get_all():
        return webapp.get(path.incarnation_path)["result"]
    assert get_all() == {}
    webapp.put(str(path), data=data)
    assert get_all() == {path.object_str: {path.key_str: data}}
    webapp.put(str(path), data=data * 2)
    assert get_all() == {path.object_str: {path.key_str: data*2}}



@pytest.fixture
def path():
    return Path()

@pytest.fixture
def saved(webapp, path, data):
    webapp.put(str(path), data=data)

class Path(object):

    def __init__(self, entity=0, incarnation=0, object=0, key=0):
        super(Path, self).__init__()
        self.entity = entity
        self.incarnation = incarnation
        self.object = object
        self.key = key

    @property
    def entity_str(self):
        return "entity{0}".format(self.entity)

    @property
    def incarnation_str(self):
        return "incarnation{0}".format(self.incarnation)

    @property
    def object_str(self):
        return "object{0}".format(self.object)

    @property
    def key_str(self):
        return "key{0}".format(self.key)


    @property
    def incarnation_path(self):
        return "/api/v1/entities/{0.entity_str}/{0.incarnation_str}".format(self)

    def __repr__(self):
        return "{0.incarnation_path}/{0.object_str}/{0.key_str}".format(self)

    def __radd__(self, other):
        return other + str(self)

    def __add__(self, other):
        return str(self) + other

@pytest.fixture
def data():
    return "some data here"


@pytest.mark.parametrize("with_empty_redis", [True, False])
def test_incarnation_change(webapp, with_empty_redis):
    if with_empty_redis:
        get_redis_connection().delete("*")
