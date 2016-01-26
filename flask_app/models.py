from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.security import UserMixin, RoleMixin

db = SQLAlchemy()

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
### Add models here

roles_users = db.Table('roles_users',
                       db.Column('user_id', db.Integer(), db.ForeignKey('user.id', ondelete='CASCADE')),
                       db.Column('role_id', db.Integer(), db.ForeignKey('role.id', ondelete='CASCADE')))


class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean())
    confirmed_at = db.Column(db.DateTime())
    roles = db.relationship('Role', secondary=roles_users,
                            backref=db.backref('users', lazy='dynamic'))
