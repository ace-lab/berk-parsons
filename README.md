# berk-parsons
A flask app for easily running experiments with Parsons Problems and common computer science interfaces.

## Virtual Environment
It is strongly encouraged to use a virtual environment, such as `virtualenv`
or conda for development. The steps below are for `virtualenv`:
1. virtualenv env
2. source env/bin/activate

After setting up the virtual environment, download the necessary libraries:
```
pip install -r requirements.txt
```

## One-time set-up
The below steps only need to be done once when you first download the application.
1. Install Postgres locally with `brew install psql`
2. In your Terminal, run `createdb parsons`
3. At the root directory of this repo, run `python` and the following commands:
```
>>> from app import db
>>> db.create_all()
>>> exit()
```

## Usage

1. Set your local environment for development by running `export FLASK_ENV=development`
2. Start Flask server by running `python3 parsons.py`

// If also starting the autograder, run the following:

3. Start Redis server using `redis-server`
4. Start grader worker using `python3 grader_worker.py`

## Seeing the First Problem
// Note: Your port number may vary
1. Go to localhost:5000/login
2. Create a user with any username
3. Go to localhost:5000/sigcse-demo

## Common Issues

### `pip install -r requirements.txt` raises `Failed building wheel for mysqlclient`
Try running `xcode-select --install` in the terminal.

### `pip install -r requirements.txt` raises `ld: library not found for -lssl`
Try running the following in the terminal:
```
$ export LDFLAGS="-L/usr/local/opt/openssl/lib"
$ export CPPFLAGS="-I/usr/local/opt/openssl/include"
```

### `redis-server` raises `command not found`
Try running `brew install redis` and then try again.

# Contributing
## Problem configuration
All problems are configured in YAML files

## Rough architecture
* `app/` contains the bulk of the application logic. This is responsible for defining routes, specifying problem sequences, rendering problems, and generally handling requests from the user.
* `grader/` is a separate surver, used to execute student Python code in a (relatively) safe way. It primarily runs code on test cases and returns results in a consistent format. It connects with the main server through rq, a redis queue library.

## Deploying to Flask
The code currently assumes a Postgres database, which Flask will automatically configure to `DATABASE_URL`.

`HIDE_TIMER` can be configured at the environment level to fully disable the timer in the upper right for all students.

We have currently set `WEB_CONCURRENCY` to 8 with standard dynos.

# Acknowledgements
* brianhsu98
* srujayk
* alexiacamacho
