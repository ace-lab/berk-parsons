import os

from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

from multiprocessing import Lock, Semaphore

app = Flask(__name__)

# Generally, these env variables shouldn't be defined locally unless

cleardb_database_url = os.getenv('CLEARDB_DATABASE_URL')
postgres_database_url = os.getenv(
    'DATABASE_URL', 'postgres://localhost/parsons')

app.config['DISABLE_LAB02'] = os.getenv('DISABLE_LAB02', False)

app.config['PRETEST_CUTOFF'] = os.getenv('PRETEST_CUTOFF', '2030')
app.config['ENABLE_MOVE_ON_MIN'] = os.getenv('ENABLE_MOVE_ON_MIN', 0)
app.config['FORCE_MOVE_ON_MIN'] = os.getenv('FORCE_MOVE_ON_MIN', None)
app.config['SKIP_LOW_PRI_EVENTS'] = os.getenv('SKIP_LOW_PRE_EVENTS', False)
app.config['HIDE_TIMER'] = os.getenv('HIDE_TIMER', False)
app.config['DISABLE_WHITELIST'] = os.getenv('DISABLE_WHITELIST', False)
# TODO(nweinman): Move to config.py file to match flask philosphy.
app.config['SQLALCHEMY_DATABASE_URI'] = postgres_database_url
# TODO: Re-enable 2nd database.
app.config['SQLALCHEMY_BINDS'] = {}
# if postgres_database_url:
#   app.config['SQLALCHEMY_BINDS'] = {'low_pri': postgres_database_url}
# else:
#   app.config['SQLALCHEMY_BINDS'] = {}
app.config['SQLALCHEMY_POOL_TIMEOUT'] = 60
app.config['SQLALCHEMY_POOL_RECYCLE'] = 3600
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
db = SQLAlchemy(app)
migrate = Migrate(app, db)
lock = Lock()
read_semaphore = Semaphore(12)

login = LoginManager(app)
login.login_view = 'login'

app.config["REDISTOGO_URL"] = os.environ.get(
    "REDISTOGO_URL", "redis://localhost:6379")
app.config['TIMEOUT'] = 10

app.config["SECRET_KEY"] = "2b9023bgs01ls"

from app import routes
