from .app import app
from flask.ext.sqlalchemy import SQLAlchemy

db = SQLAlchemy(app)

_NAME_TYPE = db.String(160)

class Record(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    entity = db.Column(_NAME_TYPE, index=True)
    incarnation = db.Column(_NAME_TYPE)
    object = db.Column(_NAME_TYPE)
    key = db.Column(_NAME_TYPE)
    value = db.Column(db.Text)
    timestamp = db.Column(db.DateTime)

db.Index('lookup', Record.entity, Record.incarnation, Record.object, Record.key, Record.timestamp)
