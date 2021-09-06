import redis
import os
import urllib
import json

from flask import Flask
from rq import Queue

GRADER_TIMEOUT = 2

app = Flask(__name__)

redis_url = os.getenv('REDISTOGO_URL', 'redis://localhost:6379')
url = urllib.parse.urlparse(redis_url)
conn = redis.Redis(host=url.hostname, port=url.port, db=0, password=url.password)

grader_queue = Queue('grader', connection=conn)

from .grade import grade
