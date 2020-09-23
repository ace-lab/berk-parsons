import os

from app import app

def run(host='127.0.0.1', debug=True):
  port = int(os.environ.get('PORT', 5000))
  for i in range(20):
      try:
        # TODO: Generalize and merge with heroku.py.
        app.run(host=host, port=port, debug=debug)
        break
      except Exception as e:
          print(str(e))
          pass

if __name__ == '__main__':
  run()
