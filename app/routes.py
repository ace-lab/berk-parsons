from . import app
from app import db, lock, read_semaphore
from datetime import datetime
import time
import json
import random
import requests
from grader import grader_queue, grade
from flask import render_template, current_app, request, session, redirect, url_for
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.urls import url_parse

from app.forms import ConsentForm, LoginForm
from app.models import Event, LowPriEvent, User, load_user, UserQuestionHistory
from .utils import load_config, load_config_file, retry_query, problem_to_hash, hash_to_problem, most_recent_parsons, md5_hash, get_cs88_sp20_group
import os

# Maybe fix user login issues.
db.init_app(app)

"""
Should make them use every part of the interface -- none of the pages should be new by the time
they start working with it.

Also, have a long line for parsons, demonstrating how you have to hover to see the entire line.

a question that touches on things
with test cases, parsons blocks
the problem should be entirely trivial to solve
point is not to make them think, but make them mess around with the interface itself
less guided than paperjs

"""

PROBLEMS_LOADED = False
LABS_TO_PROBLEMS = {}

# ------------------------------
# Routes to begin flows.
# ------------------------------
# TODO: Add decorator to ensure consent for each user.


@app.route('/test/')
@app.route('/test/start/')
@login_required
def start():
  return render_template('start.html', demo_flow=request.args.get('demo_flow'))


# @app.route('/')
# def simple_demo_start():
#   if not current_user.is_authenticated:
#     login_user(User.query.first())
#   return redirect(set_flow_internal('demo'))


@app.route('/dep-61a')
def cs61a_study_start():
  return redirect(set_flow_internal('blanks_explr_pilot_{}'.format(random.randint(0, 5))))


@app.route('/dep-61a-pt2')
def cs61a_followup_study_start():
  return redirect(set_flow_internal('blanks_explr_followup_{}'.format(random.randint(0, 1))))


@app.route('/pilot')
def semi_struct_int_pilot():
  if not current_user.is_authenticated:
    login_user(User.query.first())
  return redirect(set_flow_internal('semi_struct_int'))


@app.route('/61a')
def semi_struct_int():
  return redirect(set_flow_internal('semi_struct_int_0'))

@app.route('/88')
def semi_struct_int_88():
  return redirect(set_flow_internal('semi_struct_int_5'))

@app.route('/finish/')
@login_required
def finish():
  return render_template('finish.html')


# ------------------------------
# Routes for debugging/development.
# ------------------------------
@app.route('/set_ps')
def set_ps():
  User.update_field_for_id(current_user.id, 'treatment', 'ps')
  custom_message = None
  if app.config['ENV'] == 'development':
    custom_message = 'Your cookies are now set to the Parsons treatment'
  return render_template('403.html', custom_message=custom_message)


@app.route('/set_cd')
def set_cd():
  User.update_field_for_id(current_user.id, 'treatment', 'cd')
  custom_message = None
  if app.config['ENV'] == 'development':
    custom_message = 'Your cookies are now set to the Coding treatment'
  return render_template('403.html', custom_message=custom_message)


@app.route('/get_solution_hash/<path:problem_name>')
@login_required
def get_solution_hash(problem_name):
  # Helper method to view solution pages.
  print(problem_to_hash(problem_name))
  return render_template('403.html', custom_message='Check std out')

# ------------------------------
# Routes for displaying a set of problems.
# ------------------------------

@app.route('/sigcse-demo')
def recursion_blanks_resume():
  if not current_user.is_authenticated:
    login_user(User.query.first())
  return render_template('recursion_blanks_resume.html')

@app.route('/cs88-lab05')
@login_required
def cs88_lab05():
  problems = [
    ['Optional: Writing - Mult List', 'cs88_sp20/mult_list', 'coding'],
    ['Optional: Writing - Smallest Diff', 'cs88_sp20/smallest_diff', 'coding'],
    ['Optional: Writing - Last K Match', 'cs88_sp20/last_k_match', 'coding'],
    ['Optional: Writing - Filter Index', 'cs88_sp20/filter_index', 'coding'],
    ['Optional: Writing - Default Neighbor Reduce', 'cs88_sp20/default_neighbor_reduce', 'coding'],
    ['Optional: Writing - Apply While Small', 'cs88_sp20/apply_while_small', 'coding'],
    ['Parsons - Reverse a List', 'cs88_sp20/reverse_list', 'code_arrangement'],
    ['Parsons - Sum Digits', 'cs88_sp20/sum_digits', 'code_arrangement'],
    ['Parsons - List Digits', 'cs88_sp20/list_digits', 'code_arrangement'],
    ]

  return cs88_lab(problems, 'cs88-lab05', 'Lab 5')

def staff_whitelist(sid):
  return sid in [
  ]

def cs88_lab(problems, curr_route, problem_set):
  if problem_set[-2] == ' ':
    padded_pset = problem_set[:-1] + '0' + problem_set[-1]
  else:
    padded_pset = problem_set
  LABS_TO_PROBLEMS[padded_pset] = [problem[1] for problem in problems]

  problems_to_status = UserQuestionHistory.get_status(
    current_user.sid_hash, [problem[1] for problem in problems])

  if curr_route == 'cs88-lab07' and current_user.is_authenticated and current_user.consent == 0:
    del problems[3]

  num_problems = len(problems)
  first_unsolved_i = 0

  final_hash = False


  for problem in problems:
    if problems_to_status[problem[1]] in ['Viewed Solution', 'Solved']:
      first_unsolved_i += 1
      if problem[2] == 'tracing':
        solution_hash = problem[1]
      else:
        solution_hash = problem_to_hash(problem[1])
      if problem[2] != 'multi' and problem[2] != 'comprehension':
        problem.append('solution/{}?disable_new_tab=1&correct_only=1&next={}'.format(solution_hash, curr_route))
      else:
        problem.append(None)
      # if problem[1] in ['cs88_sp20/tree_grand_branches', 'cs88_sp20/tree_rec_coin_2', 'cs88_sp20/black_hole', 'cs88_sp20/secure_account']:
        # problem[-1] = None
    else:
      problem.append(None)
      if curr_route == 'cs88-lab01' or problem[0].startswith('Optional: '):
        first_unsolved_i += 1
        continue
      if staff_whitelist(current_user.sid_hash):
        first_unsolved_i += 1
        solution_hash = problem_to_hash(problem[1])
        if problem[2] != 'multi' not in ['multi', 'comprehension']:
          problem[-1] = ('solution/{}?disable_new_tab=1&correct_only=1&next={}'.format(solution_hash, curr_route))
      else:
        problem[0] = 'Start Question {} of {}'.format(first_unsolved_i + 1, num_problems)
        break
  else:
    if curr_route != 'cs88-lab01':
      final_hash = md5_hash(curr_route + '/' + current_user.sid_hash)

  # problems_to_status = {problem[1]:'Not started' for problem in problems}
  return render_template('problems_status.html',
    problem_set=problem_set,
    problems=problems[:first_unsolved_i+1],
    problems_to_status=problems_to_status,
    curr_route=curr_route,
    final_hash=final_hash,
    )

# ------------------------------
# Login/Consent routes.
# ------------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
  if current_user.is_authenticated:
    return redirect(url_for('cs88_lab02'))
  form = LoginForm()
  if form.validate_on_submit():
    # It appears that the database connection stays open until Python
    # garbage-collects the variable (or similar), so let's put the
    # entire function around a semaphore
    with read_semaphore:
      # Give the connection a bit of time to close.
      time.sleep(.4)
      sid_hash = User.get_sid_hash(form.student_id.data)
      user = User.query.filter_by(sid_hash=sid_hash).first()
      if user is None:
        with lock:
          user = User(sid_hash=User.get_sid_hash(form.student_id.data))
          db.session.add(user)
          db.session.commit()
      login_user(user, remember=True)
      # TODO(nweinman): Do we want to do any other validation on the value for
      # next?
      next_page = request.args.get('next')
      # if user.consent is None:
      #   next_page = url_for('consent', next='multi/cs88_sp20/demographics', final=next_page)
      if not next_page or url_parse(next_page).netloc != '':
        next_page = url_for('cs88_lab02')
      return redirect(next_page)
  return render_template('login.html', title='Sign In', form=form)


@app.route('/testing_only_logout')
def logout():
  logout_user()
  session['cached_user_meta'] = None
  return redirect(url_for('login'))

# ------------------------------
# Routes for custom flows
# ------------------------------
@app.route('/diff_estimate_0/<path:problem_name>')
@login_required
def diff_estimate_0(problem_name):
  return diff_estimate(problem_name, 'semi_struct_int_1a', 'semi_struct_int_1b')


@app.route('/diff_estimate_1/<path:problem_name>')
@login_required
def diff_estimate_1(problem_name):
  return diff_estimate(problem_name, 'semi_struct_int_2a', 'semi_struct_int_2b')


@app.route('/diff_estimate_5/<path:problem_name>')
@login_required
def diff_estimate_5(problem_name):
  return diff_estimate(problem_name, 'semi_struct_int_6a', 'semi_struct_int_6b')


@app.route('/diff_estimate_6/<path:problem_name>')
@login_required
def diff_estimate_6(problem_name):
  return diff_estimate(problem_name, 'semi_struct_int_7a', 'semi_struct_int_7b')

def diff_estimate(problem_name, hard_flow, easy_flow):
  problem_config = load_config(problem_name)
  return render_template('diff_estimate.html',
                         problem_name=problem_name,
                         problem_description=problem_config[
                             'problem_description'],
                         hard_flow=hard_flow,
                         easy_flow=easy_flow,
                         timer_start=1,
                         hide_timer=app.config['HIDE_TIMER'],
                         )

@app.route('/diff_estimate_lab07q1/<path:problem_name>')
@login_required
def diff_estimate_lab7q1(problem_name):
  return diff_estimate_q(problem_name, 'cs88_sp20/lab07q1_why', 'cs88-lab07')

@app.route('/diff_estimate_lab07q2/<path:problem_name>')
@login_required
def diff_estimate_lab7q2(problem_name):
  return diff_estimate_q(problem_name, 'cs88_sp20/lab07q2_why', 'cs88-lab07')

@app.route('/diff_estimate_lab07q3/<path:problem_name>')
@login_required
def diff_estimate_lab7q3(problem_name):
  return diff_estimate_q(problem_name, 'cs88_sp20/lab07q3_why', 'cs88-lab07')

@app.route('/diff_estimate_lab08q1/<path:problem_name>')
@login_required
def diff_estimate_lab8q1(problem_name):
  return diff_estimate_q(problem_name, 'cs88_sp20/lab08q1_why', 'cs88-lab08')

@app.route('/diff_estimate_lab08q2/<path:problem_name>')
@login_required
def diff_estimate_lab8q2(problem_name):
  return diff_estimate_q(problem_name, 'cs88_sp20/lab08q2_why', 'cs88-lab08')

@app.route('/diff_estimate_lab08q3/<path:problem_name>')
@login_required
def diff_estimate_lab8q3(problem_name):
  return diff_estimate_q(problem_name, 'cs88_sp20/lab08q3_why', 'cs88-lab08')

@app.route('/diff_estimate_lab08q4/<path:problem_name>')
@login_required
def diff_estimate_lab8q4(problem_name):
  return diff_estimate_q(problem_name, 'cs88_sp20/lab08q4_why', 'cs88-lab08')

@app.route('/diff_estimate_lab08q5/<path:problem_name>')
@login_required
def diff_estimate_lab8q5(problem_name):
  return diff_estimate_q(problem_name, 'cs88_sp20/lab08q5_why', 'cs88-lab08')

def diff_estimate_q(problem_name, multi_name, final):
  problem_config = load_config(problem_name)
  return render_template('diff_estimate_questions.html',
                         problem_name=problem_name,
                         multi_name=multi_name,
                         final=final,
                         problem_description=problem_config[
                             'problem_description'],
                         timer_start=1,
                         hide_timer=app.config['HIDE_TIMER'],
                         )

# ------------------------------
# Routes for exercises
# ------------------------------


@app.route('/multi/<path:problem_name>')
@login_required
def multi(problem_name):
  # TODO: A lot of this code is boiler plate and could be DRYed.
  if problem_name == None:
    problem_name = 'pre_test_comp'

  next_problem = get_next_problem(problem_name, 'multi')

  extra_args = {}
  if problem_name == 'pre_test_comp_2':
    extra_args['timer_start'] = get_problem_start('multi', problem_name)

  problem_config = load_config(problem_name)
  return render_template('multi.html',
                         problem_name=problem_name,
                         problems=problem_config,
                         next_problem=next_problem,
                         hide_timer=app.config['HIDE_TIMER'],
                         **extra_args
                         )


# A coding interface which also asks participants to write out their approach.
@app.route('/coding_comp/<path:problem_name>')
@login_required
def multi_code(problem_name):
  if app.config['PRETEST_CUTOFF'] and str(datetime.utcnow()) > app.config['PRETEST_CUTOFF']:
    return redirect('multi/19s_algo_study/demographics')

  next_problem = get_next_problem(problem_name, 'coding_comp')

  timer_start = get_problem_start('multi', 'pre_test_comp_2')

  problem_config = load_config(problem_name)
  return render_template(
      "coding.html",
      problem_name=problem_name,
      algorithm_description=problem_config['algorithm_description'],
      problem_description=problem_config['problem_description'],
      is_algorithm_implementation=None,
      is_testable=False,
      timer_start=timer_start,
      hide_timer=app.config['HIDE_TIMER'],
      show_approach_input=True,
      next_problem=next_problem,
      initial_code=problem_config['initial_code'])


@app.route('/code_skeleton/<path:problem_name>')
@login_required
def code_skeleton(problem_name):
  return parsons(problem_name, code_skeleton=True)


@app.route('/code_arrangement/<path:problem_name>')
@login_required
def parsons(problem_name, code_skeleton=False):
  next_problem = get_next_problem(problem_name, "code_arrangement")
  back_url = None
  if request.args.get('final'):
    back_url = '/{}'.format(request.args.get('final'))

  timer_start = get_problem_start('parsons', problem_name)

  problem_config = load_config(problem_name)

  with read_semaphore:
    time.sleep(.4)
    most_recent_code = Event.most_recent_code(
        current_user.id, problem_name, 'parsons')
  code_lines = problem_config['code_lines'] + \
      '\nprint(!BLANK)' * 3 + '\n# !BLANK' * 3
  if most_recent_code:
    code_lines = most_recent_parsons(most_recent_code, code_lines)
  return render_template("parsons.html",
                         problem_name=problem_name,
                         algorithm_description=problem_config[
                             'algorithm_description'],
                         problem_description=problem_config[
                             'problem_description'],
                         timer_start=timer_start,
                         hide_timer=app.config['HIDE_TIMER'],
                         # TODO(nweinman): Better UI for this (and comment
                         # lines as well)
                         code_lines=code_lines,
                         next_problem=next_problem,
                         back_url=back_url,
                         code_skeleton=code_skeleton,
                         )


@app.route('/coding/<path:problem_name>')
@login_required
def coding(problem_name):
  if problem_name == None:
    problem_name = "binary_search_1"

  next_problem = get_next_problem(problem_name, "coding")
  back_url = None
  if request.args.get('final'):
    back_url = '/{}'.format(request.args.get('final'))
  problem_config = load_config(problem_name)

  timer_start = get_problem_start('coding', problem_name)

  problem_config = load_config(problem_name)
  with read_semaphore:
    time.sleep(.4)
    most_recent_code = Event.most_recent_code(
        current_user.id, problem_name, 'coding')
  initial_code = most_recent_code or problem_config['initial_code']

  return render_template("coding.html",
                         problem_name=problem_name,
                         algorithm_description=problem_config[
                             'algorithm_description'],
                         problem_description=problem_config[
                             'problem_description'],
                         timer_start=timer_start,
                         hide_timer=app.config['HIDE_TIMER'],
                         pseudocode=problem_config['pseudocode'],
                         is_algorithm_implementation=problem_config[
                             'is_algorithm_implementation'],
                         is_testable=True,
                         next_problem=next_problem,
                         back_url=back_url,
                         initial_code=initial_code)


@app.route('/tracing/<problem_hash>')
@login_required
def tracing(problem_hash):
  problem_name = hash_to_problem(problem_hash)
  next_problem = get_next_problem(problem_name, "tracing")
  back_url = None
  if request.args.get('final'):
    back_url = '/{}'.format(request.args.get('final'))
  problem_config = load_config(problem_name)

  timer_start = get_problem_start('coding', problem_name)

  problem_config = load_config(problem_name)

  test_inputs = []
  if problem_config['custom_tracing_tests']:
    test_inputs = problem_config['custom_tracing_tests']
  else:
    for test_input in problem_config['test_cases'][:3]:
      test_inputs.append('function({})'.format(
        ', '.join([str(arg) for arg in test_input['fn_args']])))

  return render_template("tracing.html",
                         problem_name=problem_name,
                         problem_hash=problem_hash,
                         obscure_code=problem_config['obscure_code'],
                         test_inputs=test_inputs,
                         timer_start=timer_start,
                         hide_timer=app.config['HIDE_TIMER'],
                         disable_problem_statement=True,
                         next_problem=next_problem,
                         back_url=back_url
                         )


@app.route('/comprehension/<path:problem_name>')
@login_required
def comprehension(problem_name):
  next_problem = get_next_problem(problem_name, "comprehension")

  problem_config = load_config(problem_name)
  choices = []
  for i in range(len(problem_config['choices'])):
    choices.append((str(i), problem_config['choices'][i]))
  return render_template('comprehension.html',
                         problem_name=problem_name,
                         algorithm_description=problem_config[
                             'algorithm_description'],
                         problem_description=problem_config[
                             'problem_description'],
                         choices=choices,
                         correct_answer=problem_config['correct_answer'],
                         next_problem=next_problem,
                         pseudocode=problem_config['pseudocode'])


@app.route('/solution/<problem_hash>')
@login_required
def solution(problem_hash):
  problem_name = hash_to_problem(problem_hash)

  next_problem = get_next_problem(problem_name, 'solution')
  problem_config = load_config(problem_name)
  with read_semaphore:
    time.sleep(.4)
    most_recent_code = Event.most_recent_code(
        current_user.id, problem_name, None)

  return render_template('solution.html',
                         algorithm_description=problem_config[
                             'algorithm_description'],
                         problem_description=problem_config[
                             'problem_description'],
                         problem_name=problem_name,
                         pseudocode=problem_config['pseudocode'],
                         most_recent_code=most_recent_code,
                         solution=problem_config['solution'],
                         is_algorithm_implementation=problem_config[
                             'is_algorithm_implementation'],
                         next_problem=next_problem,
                         disable_new_tab=request.args.get('disable_new_tab'),
                         correct_only='correct_only' in request.args,
                         )


# ------------------------------
# POST request routes
# ------------------------------
@app.route('/log_event/', methods=['POST'])
def log_event():
  if current_user.consent == 0:
    return 'not logging'
  try:
    data = request.form.to_dict(flat=False)
    print(data)
    ts = datetime.utcnow()
    with lock:
      if 'log_level' in data and data['log_level'] == ['LowPri']:
        if app.config['SKIP_LOW_PRI_EVENTS']:
          return 'skipped'
        event = LowPriEvent()
        event.process_id = os.getpid()
      else:
        event = Event()
      db.session.add(event)
      db.session.commit()
      event.question_type = data['question_type']
      event.question_name = data['question_name']
      event.event_type = data['event_type']
      event.current_state = data['current_state']
      event.user_id = current_user.id
      event.ts = ts
      db.session.commit()
  except Exception as e:
    print(e)
  finally:
    # Old code to double-log locally in case the database drops any entries.
    # if 'log_level' in data and data['log_level'] == ['INFO']:
      # return 'not logged'
    # requests.post('http://d5edce65.ngrok.io/log_local/', data={
    #     'question_type': data['question_type'],
    #     'question_name': data['question_name'],
    #     'event_type': data['event_type'],
    #     'current_state': data['current_state'],
    #     'user_id': current_user.id,
    #     'ts': ts,
    # })
    return 'logged'

@app.route('/update_user_question_history/', methods=['POST'])
def update_user_question_history():
  data = request.form.to_dict(flat=False)
  UserQuestionHistory.update_status(
    current_user.sid_hash,
    data['question_name'][0],
    int(data['status'][0]))
  return 'success'

# @app.route('/log_local/', methods=['POST'])
# def log_local():
#   if app.config['ENV'] == 'development':
#     import os
#     with open('data/logs_{}.log'.format(request.form.get('user_id')), 'a') as f:
#       f.write(json.dumps(request.form.to_dict(flat=False)) + '\n')
#   return ''


@app.route('/submit/', methods=['POST'])
def submit():
  problem_name = request.form['problem_name']
  submitted_code = request.form['submitted_code']
  problem_config = load_config(problem_name)
  pre_test_code = problem_config['pre_test_code'] or ''
  test_code = problem_config['test_code'] or ''
  try:
    grader_results = submit_to_grader(
        pre_test_code + submitted_code + test_code,
        problem_config['test_cases'], problem_config['test_fn'])
  except Exception as e:
    test_results = '<div class="testcase {}"><span class="msg">{}</span></div>'.format(
        "error", str(e))
    return json.dumps({'correct': 0, 'test_results': test_results})

  test_results, correct = parse_results(grader_results)
  print('\n')
  print(current_user.sid_hash, current_user.consent, correct)
  print('\n')
  # print(correct)
  # print('\n'*3)

  return json.dumps({'correct': correct, 'test_results': test_results})

from operator import add, mul, sub

@app.route('/submit_tracing/', methods=['POST'])
def submit_tracing():
  code = request.form['code']
  answers = request.form['answers']
  exec(code)
  test_results = []
  for ans in json.loads(answers):
    correct = False
    try:
      correct = eval(ans['id']) == eval(ans['input'], {"__builtins__":None}, {})
    except:
      pass
    if correct:
      test_results.append('testcase pass')
    else:
      test_results.append('testcase fail')
  return json.dumps({'test_results': test_results})


@app.route('/set_flow/', methods=['POST'])
def set_flow():
  flow_id = request.form['flow_id']
  return set_flow_internal(flow_id)

# ------------------------------
# Helper functions.
# ------------------------------
def get_next_problem(current_problem_name, current_problem_type):
  if current_problem_name == 'cs88_sp20/demographics_12':
    return "/multi/cs88_sp20/survey_12_fin"
  next_arg = request.args.get('next')
  final_arg = request.args.get('final')
  final_url_arg = '?'
  if final_arg:
    final_url_arg = '?final={}'.format(final_arg)
  if next_arg:
    return "/{}{}".format(next_arg, final_url_arg)

  # Unless otherwise specified, always show the solution (breaks some old studies :/)
  # if 'flow' not in session and current_problem_type in ['coding', 'code_arrangement', 'tracing']:
  if current_problem_type in ['coding', 'code_arrangement', 'tracing']:
    return '/solution/{}{}&disable_new_tab=1'.format(problem_to_hash(current_problem_name), final_url_arg)

  if final_arg:
    return "/{}".format(final_arg)
  if 'flow' in session:
    flows = load_config_file("problems/flows.yaml")
    current_flow = flows[session['flow']]
    current_flow_index = 0
    for i in range(len(current_flow)):
      if current_flow[i]['type'] == current_problem_type and current_flow[i]['problem_name'] == current_problem_name:
        current_flow_index = i
    session['flow_index'] = current_flow_index + 1
    if session['flow_index'] < len(current_flow):
      next_problem = current_flow[session['flow_index']]
      if next_problem['type'] == 'solution':
        next_problem = "/" + \
            next_problem['type'] + "/" + \
            problem_to_hash(next_problem['problem_name']) + \
            "?problem_name=" + next_problem['problem_name']
      else:
        next_problem = "/" + \
            next_problem['type'] + "/" + next_problem['problem_name']
    else:
      next_problem = "/finish"
  else:
    next_problem = "/finish"
  return next_problem


def set_flow_internal(flow_id):
  session['flow'] = flow_id
  session['flow_index'] = 0
  flows = load_config_file("problems/flows.yaml")
  current_flow = flows[session['flow']]
  if session['flow_index'] < len(current_flow):
    next_problem = current_flow[session['flow_index']]
    next_problem = "/" + next_problem['type'] + \
        "/" + next_problem['problem_name']
  else:
    next_problem = "/finish"
  return next_problem


# If this problem has been loaded previously, get the time of the inital
# loading.
def get_problem_start(question_type, problem_name):
  if 'disable_timer' in request.args:
    return None
  if question_type == 'multi' and problem_name == 'pre_test_comp_2':
    if 'comp_start' in session:
      return int((datetime.utcnow() - session['comp_start']).total_seconds())
  with read_semaphore:
    time.sleep(.4)
    # TODO: See if this will mess up query limits significantly :/
    try:
      print("get problem start for user {}".format(current_user.id))
      first_load = retry_query(lambda: Event.query.filter_by(
          user_id=current_user.id,
          question_name='{' + problem_name + '}',
          question_type='{' + question_type + '}',
          event_type='{load}'
      ).order_by(Event.ts.asc()).first())
    except:
      first_load = None
    if question_type == 'multi' and problem_name == 'pre_test_comp_2':
      comp_start = datetime.utcnow()
      if first_load:
        comp_start = first_load.ts
      session['comp_start'] = comp_start
      int((datetime.utcnow() - session['comp_start']).total_seconds())
    if first_load:
      return int((datetime.utcnow() - first_load.ts).total_seconds())
    return 1


# ------------------------ GRADING ------------------------


def submit_to_grader(code, tests, function_name=None):
  """
  Tests the code
  Args:
      code (str): A string containing student submitted code
      tests (list of lists): Contains the tests to be run using the code. Each list's first value should be another
      list containing the desired inputs, and the second value should be the expected output. For example, to run
      the tests add_up(1, [1, 2, 3]) with expected output False and the test add_up(3, [1, 2, 3]) with expected
      output True, the input should look like [[[1, [1, 2, 3]], False], [[3, [1, 2, 3]], True]]
      function_name (str): The function name to be tested. Optional: the tester will automatically run the tests
      on the defined function if no function name is passed in
  Returns:
      list of dictionaries, one dictionary for every test containing the results.
  """
  try:
    job = grader_queue.enqueue(grade, code, tests, function_name)
  except Exception as e:
    # TODO: Contact info
    raise Exception("Error connecting to Redis server. Contact someone!")
  start_time = int(time.time())
  while not job.is_finished and int(time.time() - start_time) < current_app.config["TIMEOUT"]:
    if job.is_failed:
      # TODO: Contact info
      raise Exception("Worker job failed. Try submitting again!")
    time.sleep(0.1)
  else:
    if job.is_finished:
      return job.result
    # TODO: Contact info
    raise Exception("Grader request timed out! Try submitting again!")


def parse_results(grader_results):
  """
  Parses the grader results, readying them for output to the front-end
  Args:
      grader_results: A list of dictionaries, with one dictionary for each test ran.
  Returns:
      html: The HTML code corresponding to the results of all the tests.
      correct: 1 if all the tests passed, 0 if there were errors or incorrect results.
  """
  html = ''
  correct = 1
  if not grader_results:
    raise Exception("No test results found for this problem.")
  for test in grader_results:
    html += '<div class="testcase {}">'.format(test['status'])
    if test['function_name']:
      html += '<span class="msg">Calling function <code>{}({})</code>.</span><br />'.\
          format(test['function_name'], test['input'])
    if test['status'] == 'fail':
      correct = 0
    if test['status'] == 'error':
      html += '<span class="msg">{}</span><br /><span class="errormsg">{}</span><br />'.format(
          'Error in parsing/executing your program', test['error_msg'])
      correct = 0
    else:
      # TODO: De-Stringify?
      if test['expected'] == 'None':
        if test['actual'] != 'None':
          html += '<span class="msg"><code>{}</code></span> <br />'.format(test[
                                                                           'actual'])
      else:
        html += '<span class="msg">Expected result to be <code>{}</code> , your code returned ' \
                '<code>{}</code></span> <br />'.format(
                    test['expected'], test['actual'])

    if test['printed']:
      test['printed'] = test['printed'].replace('<', '&lt;').replace('>', '&gt;')
      html += '<span class="msg">Print Output: <pre>{}</pre></span>'.format(test[
                                                                            'printed'])

    html += '</div>'

    if test['status'] != 'pass':
      break

  return html, correct
