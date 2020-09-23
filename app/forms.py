from flask_wtf import FlaskForm
from wtforms import RadioField, StringField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Length, ValidationError

from . import app
from app.models import User
from app.utils import load_config

WHITELIST = []

def sid_hash_whitelist(form, field):
  if not app.config['DISABLE_WHITELIST']:
    if WHITELIST and User.get_sid_hash(field.data) not in WHITELIST:
      raise ValidationError(
        'That email address is not in the class roster. If you believe this ' +
        'is in error, please contact nweinman@berkeley.edu and ball@berkeley.edu ' +
        'with the email address you used.')


class LoginForm(FlaskForm):
  student_id = StringField('Email Address', validators=[DataRequired(), sid_hash_whitelist])
  student_id2 = StringField('Confirm Email Address', validators=[
                            DataRequired(), EqualTo('student_id')])
  submit = SubmitField('Sign In')



class ConsentForm(FlaskForm):
  consent = RadioField('', choices=[
      ('1', 'I agree that I am 18 years or older and consent to my data being used anonymously to improve CS Education.'),
      ('0', 'I do not consent to my data being used or I am younger than 18 years old.')])
  submit = SubmitField('Confirm')
