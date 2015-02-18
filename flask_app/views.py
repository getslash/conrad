import collections
import datetime
import random
import time
import sys

import logbook
from flask import abort, jsonify, make_response, render_template, request

from redis import Redis
from sqlalchemy import desc

from .app import app
from .models import db, Record

_redis_connection = None


def get_redis_connection():
    global _redis_connection
    if _redis_connection is None:
        _redis_connection = Redis()
    return _redis_connection


@app.route("/")
def index():
    return render_template("index.html", version=sys.version)

# For example: /api/v1/entities/ibox506/<deployment UUID>/volume:2387/infinio_serialized_data <-- "bla"
@app.route("/api/v1/entities/<entity>/<incarnation>/<object>/<key>", methods=["get", "put"])
def get_or_put_attribute(entity, incarnation, object, key):
    if request.method.lower() == "get":
        return get_attribute(entity, incarnation, object, key)
    return put_attribute(entity, incarnation, object, key)


def get_attribute(entity, incarnation, object, key):
    returned = _get_cached_result(entity, incarnation, object, key)
    if returned is None:
        record = Record.query.filter(
            Record.entity == entity, Record.incarnation == incarnation,
            Record.object == object, Record.key == key).order_by(desc(Record.timestamp)).first()
        if record is None:
            abort(404)
        returned = record.value
        _cache_result(entity, incarnation, object, key, returned)

    if request.args.get("raw", "").lower() in ("true", "yes"):
        return make_response(returned)
    return jsonify({"result": returned})

def _entity_incarnation_key(entity):
    return "entity-incarnation.{}".format(entity)

def _entity_salt_key(entity):
    return "entity-salt.{}".format(entity)

def put_attribute(entity, incarnation, object, key):
    timestamp = datetime.datetime.utcnow()
    data = request.input_stream.read()
    record = Record(entity=entity, incarnation=incarnation, object=object,
                    key=key, value=data, timestamp=timestamp)
    redis = get_redis_connection()
    prev_incarnation = redis.getset(
        _entity_incarnation_key(entity), incarnation)
    if prev_incarnation is None or prev_incarnation != incarnation:
        _invalidate_entity_cache(entity)
        logbook.debug(
            "Incarnation has changed for {} (prev: {}, new: {})", entity, prev_incarnation, incarnation)
        Record.query.filter(Record.entity == entity,
                            Record.incarnation != incarnation).delete()
    redis.expire(_entity_incarnation_key(entity), _ENTITY_INCARNATION_EXPIRY)
    db.session.add(record)
    db.session.commit()
    _cache_result(entity, incarnation, object, key, data)
    return jsonify({"result": True})


def _get_cached_result(entity, incarnation, object, key):
    redis_key = _generate_redis_key(entity, incarnation, object, key)
    returned = get_redis_connection().get(redis_key)
    if returned is not None:
        # refresh the key's expiry
        get_redis_connection().expire(redis_key, _CACHE_EXPIRY_TIME)
    return returned

MINUTE = 60
HOUR = 60 * MINUTE
_CACHE_EXPIRY_TIME = 1 * HOUR
_ENTITY_INCARNATION_EXPIRY = 7 * 24 * HOUR


def _cache_result(entity, incarnation, object, key, value):
    get_redis_connection().setex(
        _generate_redis_key(entity, incarnation, object, key), value, _CACHE_EXPIRY_TIME)


def _invalidate_entity_cache(entity):
    get_redis_connection().delete(_entity_salt_key(entity))


def _generate_redis_key(entity, *fragments):
    parts = ["", get_entity_key_salt(entity), entity]
    parts.extend(fragments)
    return "/".join(str(x) for x in parts)


def get_entity_key_salt(entity):
    redis = get_redis_connection()
    generation = _get_new_entity_key_salt()
    key = _entity_salt_key(entity)
    if redis.setnx(key, generation):
        redis.expire(key, _ENTITY_INCARNATION_EXPIRY)
        return generation
    return redis.get(key)


def _get_new_entity_key_salt():
    return (time.time() * 1000) + random.randrange(1000)


@app.route("/api/v1/entities/<entity>/<incarnation>")
def get_all_incarnation_tags(entity, incarnation):
    records = Record.query.filter(
        Record.entity == entity, Record.incarnation == incarnation).order_by(Record.timestamp)
    returned = collections.defaultdict(dict)
    for record in records:
        returned[record.object][record.key] = record.value
    return jsonify({"result": returned})
