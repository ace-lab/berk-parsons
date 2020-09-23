# Required set-up for Heroku.
web: gunicorn app:app --preload
# web: gunicorn app:app
worker: python3 -u grader_worker.py
