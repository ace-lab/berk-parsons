import redis
import os
import urllib
import json

from flask import Flask
from rq import Queue
from rq.serializers import JSONSerializer

GRADER_TIMEOUT = 2

app = Flask(__name__)

redis_url = os.getenv('REDISTOGO_URL', 'redis://localhost:6379')
url = urllib.parse.urlparse(redis_url)
conn = redis.Redis(host=url.hostname, port=url.port, db=0, password=url.password)

python_grader_queue = Queue('grader', connection=conn, serializer=JSONSerializer)
ruby_grader_queue = Queue('grader-ruby', connection=conn, serializer=JSONSerializer)

from .grade import grade
