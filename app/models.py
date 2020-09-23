import hashlib
import json
import urllib.parse

from app import app, db, login, lock
from collections import defaultdict
from datetime import datetime
from flask import has_request_context, session, request
from flask_login import UserMixin
from sqlalchemy import event
from .utils import retry_query, md5_hash


USER_SID_LEN = 100
QUESTION_NAME_LEN = 64


class User(UserMixin, db.Model):
  __tablename__ = 'users'

  id = db.Column(db.Integer, primary_key=True)
  sid_hash = db.Column(db.String(USER_SID_LEN), index=True, unique=True)
  consent = db.Column(db.Integer)
  treatment = db.Column(db.String(30))
  ts_created = db.Column(db.DateTime, index=True, default=datetime.utcnow)

  @staticmethod
  def get_sid_hash(sid):
    # TODO: Switch to SHA512 or similar
    return md5_hash(sid)

  @staticmethod
  def update_field_for_id(user_id, field, value):
    user = retry_query(lambda: User.query.get(int(user_id)))
    setattr(user, field, value)
    with lock:
      db.session.commit()

  def __repr__(self):
    return '<User {}>'.format(self.sid_hash)


@event.listens_for(db.session, 'before_flush')
def receive_before_flush(db_session, flush_context, instances):
  if has_request_context():
    for changing_obj in db_session.dirty:
      if type(changing_obj) is User:
        session['cached_user_meta'] = None


@login.user_loader
def load_user(id):
  if not session.get('cached_user_meta'):
    user = retry_query(lambda: User.query.get(int(id)))
    if not user:
      return user
    session['cached_user_meta'] = {
        col.name: getattr(user, col.name) for col in User.__table__.columns
    }
  return User(**session['cached_user_meta'])


class Event(db.Model):
  __tablename__ = 'events'

  id = db.Column(db.Integer, primary_key=True)
  # TODO: Change these into an enum if necessary for efficiency.
  question_type = db.Column(db.String(32))
  question_name = db.Column(db.String(QUESTION_NAME_LEN))
  event_type = db.Column(db.String(32))
  current_state = db.Column(db.Text)
  ts = db.Column(db.DateTime, index=True, default=datetime.utcnow)
  user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

  @staticmethod
  def most_recent_code(user_id, problem_name, problem_type):
    return None

    def most_recent_code_query():
      filters = {'user_id': user_id, 'question_name': problem_name}
      if problem_type:
        filters['question_type'] = problem_type
      return Event.query.filter_by(**filters).\
          filter((Event.event_type == 'unload') | (Event.event_type == 'submit') | (Event.event_type == 'move_on')).\
          order_by(Event.ts.desc()).first()

    problem_type_prefix = problem_type + '/' if problem_type else ''
    encoded_problem_name = urllib.parse.quote(
        problem_type_prefix + problem_name, 'utf-8')
    if encoded_problem_name in request.cookies:
      encoded_lines = request.cookies.get(encoded_problem_name)
      decoded_lines = urllib.parse.unquote(encoded_lines)
      return json.loads(decoded_lines)['code']
    most_recent_event = retry_query(most_recent_code_query)
    try:
      return json.loads(most_recent_event.current_state)['code']
    except:
      return None

  def __repr__(self):
    return '<Event {} {}>'.format(self.question_name, self.event_type)


class UserQuestionHistory(db.Model):
  __tablename__ = 'user_question_history'

  id = db.Column(db.Integer, primary_key=True)
  user = db.Column(db.String(USER_SID_LEN), index=True)
  question_name = db.Column(db.String(QUESTION_NAME_LEN), index=True)
  # 0: Unopened, 1: Attempted, 2: Viewed Solution, 3: Solved
  status = db.Column(db.Integer)
  ts = db.Column(db.DateTime, index=True, default=datetime.utcnow)

  @classmethod
  def __get_status_entries(cls, user, question_names):
    print(question_names)
    return cls.query.filter(cls.user == user).\
      filter(cls.question_name.in_(question_names)).all()
    # return retry_query(cls.query.filter(cls.user == user).\
      # filter(cls.question_name.in_(question_names)).all())

  @classmethod
  def get_status(cls, user, question_names):
    entries = cls.__get_status_entries(user, question_names)
    print(entries, user, question_names)
    question_names_to_status = defaultdict(lambda: 'Not Started')
    for entry in entries:
      print('debug', entry)
      human_status = ''
      if entry.status == 0:
        human_status = 'Not Started'
      if entry.status == 1:
        human_status = 'Started'
      if entry.status == 2:
        human_status = 'Viewed Solution'
      if entry.status == 3:
        human_status = 'Solved'
      question_names_to_status[entry.question_name] = human_status
    return question_names_to_status

  @classmethod
  def update_status(cls, user, question_name, status):
    with lock:
      entries = cls.__get_status_entries(user, [question_name])
      if entries:
        entry = entries[0]
        if entry.status >= status:
          return
        setattr(entry, 'status', status)
        setattr(entry, 'ts', datetime.utcnow())
      else:
        entry = cls(user=user, question_name=question_name, status=status)
        db.session.add(entry)
      db.session.commit()

class LowPriEvent(db.Model):
  __tablename__ = 'lowprievents'
  id = db.Column(db.Integer, primary_key=True)
  question_type = db.Column(db.String(32))
  question_name = db.Column(db.String(64))
  event_type = db.Column(db.String(32))
  current_state = db.Column(db.Text)
  process_id = db.Column(db.Integer)
  ts = db.Column(db.DateTime, index=True, default=datetime.utcnow)
  user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

  def __repr__(self):
    return '<LowPriEvent {} {}>'.format(self.question_name, self.event_type)
