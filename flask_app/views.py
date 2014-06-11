import collections
import datetime
import logbook

from flask import jsonify, make_response, render_template, request, abort

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
    return render_template("index.html")


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


def _get_cached_result(entity, incarnation, object, key):
    redis_key = _generate_redis_key(entity, incarnation, object, key)
    return get_redis_connection().get(redis_key)

MINUTE = 60
HOUR = 60 * MINUTE
_CACHE_EXPIRY_TIME = 1 * HOUR


def _cache_result(entity, incarnation, object, key, value):
    get_redis_connection().setex(
        _generate_redis_key(entity, incarnation, object, key), value, _CACHE_EXPIRY_TIME)


def _generate_redis_key(*fragments):
    return "/" + "/".join(fragment.replace("\\", "\\\\").replace("/", "\\/") for fragment in fragments)


def put_attribute(entity, incarnation, object, key):
    timestamp = datetime.datetime.utcnow()
    data = request.data or request.stream.read()
    record = Record(entity=entity, incarnation=incarnation, object=object,
                    key=key, value=data, timestamp=timestamp)
    prev_incarnation = get_redis_connection().getset(
        "entity-incarnation.{0}".format(entity), incarnation)
    if prev_incarnation is None or prev_incarnation != incarnation:
        logbook.debug(
            "Incarnation has changed for {} (prev: {}, new: {})", entity, prev_incarnation, incarnation)
        Record.query.filter(Record.entity == entity,
                            Record.incarnation != incarnation).delete()
    db.session.add(record)
    db.session.commit()
    _cache_result(entity, incarnation, object, key, data)
    return jsonify({"result": True})


@app.route("/api/v1/entities/<entity>/<incarnation>")
def get_all_incarnation_tags(entity, incarnation):
    records = Record.query.filter(
        Record.entity == entity, Record.incarnation == incarnation).order_by(Record.timestamp)
    returned = collections.defaultdict(dict)
    for record in records:
        returned[record.object][record.key] = record.value
    return jsonify({"result": returned})
