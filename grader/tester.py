import copy
import re
import signal
import unittest
import io
import sys
import traceback
from contextlib import redirect_stdout
from . import GRADER_TIMEOUT


def e_to_str(e):
  return '{}: {}'.format(type(e).__name__, e)


def clean_globals(orig_globals):
  g = globals()
  vars_to_delete = []
  for var in g:
    if var not in orig_globals:
      vars_to_delete.append(var)
    else:
      g[var] = orig_globals[var]
  for var in vars_to_delete:
    del g[var]


class Timeout:
  """
  A class to allow timing out function calls if they take too long. Warning: UNIX only (requires signal package)
  Credit: https://stackoverflow.com/questions/2281850/timeout-function-if-it-takes-too-long-to-finish
  """

  def __init__(self, seconds=1, error_message='Timeout'):
    self.seconds = seconds
    self.error_message = error_message

  def handle_timeout(self, signum, frame):
    raise TimeoutError(self.error_message)

  def __enter__(self):
    signal.signal(signal.SIGALRM, self.handle_timeout)
    signal.alarm(self.seconds)

  def __exit__(self, type, value, traceback):
    signal.alarm(0)


class Tester:
  """
  A class for testing student submissions
  Attributes:
      - code: Student submitted code to be tested
      - tests: A list of dictionaries. Each dictionary has two fields, fn_args and expected.
               fn_args should be a list of arguments.
               [{'fn_args': [*fn_args], 'expected': expected}, ... ]
               ex. [{'fn_args': [3, [1, 2, 3]], 'expected': True}] for add_up(3, [1, 2, 3])
      - function_name: If specified, function_name will be the function that is run with the given input.
                       If not specified, the tests will run on the first defined function.
  """

  def __init__(self, code, tests, function_name):
    self.code = code
    self.tests = tests
    self.results = []
    self.function_name = function_name

  def test(self):
    orig_globals = copy.copy(globals())
    try:
      with Timeout(seconds=GRADER_TIMEOUT,
                   error_message="Running your code took too long! "
                                 "Check for any infinite loops outside of the function definition."):
        exec(self.code, globals())
    except Exception as e:
      self.append_result('error', e_to_str(e))
      clean_globals(orig_globals)
      return

    if self.function_name:
      function_name = self.function_name
    else:
      try:
        function_name = get_function_name(str(self.code))
      except Exception as e:
        self.append_result(
            'error', "Could not find a function. Make sure one is defined.")
        clean_globals(orig_globals)
        return

    try:
      function = globals()[function_name]
    except KeyError:
      self.append_result(
          'error', '{} not defined! Check for any typos'.format(function_name))
      clean_globals(orig_globals)
      return

    test_case = unittest.TestCase()
    for test in self.tests:
      fn_args = test['fn_args']
      expected = test['expected']

      printed = io.StringIO()
      # For displaying to the user
      input = str(fn_args)[1:-1]

      with redirect_stdout(printed):
        try:
          with Timeout(seconds=GRADER_TIMEOUT,
                       error_message="Function call took too long! "
                                     "Check for any infinite loops."):
            if fn_args == "None":
              actual = function()
            else:
              actual = function(*fn_args)
        except TimeoutError as e:
          self.append_result('error', e_to_str(e), input=input,
                             function_name=function_name, printed=printed)
          # To prevent clogging up the worker, stop testing if a timeout is
          # reached
          break
        except Exception as e:
          try:
            exc_type, exc_obj, exc_traceback = sys.exc_info()
            student_traceback = exc_traceback

            while student_traceback.tb_next is not None:
              student_traceback = student_traceback.tb_next
            line_number = student_traceback.tb_lineno
            traceback_string = ", line " + str(line_number)
          except:
            traceback_string = ""

          error_msg = e_to_str(e) + traceback_string
          self.append_result('error', error_msg, input=input,
                             function_name=function_name, printed=printed)
          continue

      status = 'pass'
      error_msg = None
      try:
        test_case.assertEqual(expected, actual)
      except AssertionError as e:
        status = 'fail'
        error_msg = e_to_str(e)
      finally:
        self.append_result(status, error_msg, expected=str(expected), actual=str(actual),
                           input=input, function_name=function_name, printed=printed)
    clean_globals(orig_globals)

  def append_result(self, status, error_msg, input=None, function_name=None, actual=None, expected=None, printed=None):
    if printed is not None:
      printed_lines = printed.getvalue().split('\n')
      top_limit = 20
      bottom_limit = 10
      if len(printed_lines) >= top_limit + bottom_limit:
        printed_lines = printed_lines[:top_limit] + \
            ['...'] + printed_lines[-bottom_limit:]
      printed = '\n'.join(printed_lines)
    self.results.append({'status': status, 'error_msg': error_msg, 'function_name': function_name, 'input': input,
                         'actual': actual, 'expected': expected, 'printed': printed})

  def get_results(self):
    return self.results


def get_function_name(code):
  """
  Finds a defined function given a string of code.
  code (str): The inputted code
  returns (str): The defined function name
  """
  pattern = re.compile('(?<=def )[ ]*\w+')
  search_results = re.findall(pattern,  code)
  result = search_results[0]
  result = result.replace(" ", "")
  return result
