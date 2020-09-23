# Can be run with python -m unittest app/tests/utils_test.py
import unittest
from unittest.mock import Mock, patch

from pathlib import PosixPath

from app.utils import *


class TestCase(unittest.TestCase):

  def setUp(self):
    pass

  def tearDown(self):
    pass

  @patch('time.sleep', return_value=None)
  def test_retry_query(self, mock_sleep):
    success_fn = Mock()
    exception_fn = Mock(side_effect=Exception())

    # Functions should only be run once if they succeed
    retry_query(success_fn)
    assert success_fn.called
    assert success_fn.call_count == 1
    assert not mock_sleep.called

    # Functions should be run several times before giving up if they fail.
    with self.assertRaises(Exception) as _:
      retry_query(exception_fn)

    assert exception_fn.called
    assert exception_fn.call_count == 4
    assert mock_sleep.called
    assert mock_sleep.call_count == 3

  @patch('pathlib.PosixPath.__init__', wraps=PosixPath.__init__)
  def test_hash_cache(self, mock_path):
    test_hash = problem_to_hash('demo')
    problem_name = hash_to_problem(test_hash)

    self.assertEqual('demo', problem_name)
    call_count = mock_path.call_count
    assert call_count > 0

    test_hash2 = problem_to_hash('19s_early_pilots/tutorial')
    problem_name2 = hash_to_problem(test_hash2)

    assert mock_path.call_count == call_count

    with self.assertRaises(KeyError) as _:
      hash_to_problem('12345hash')

  def test_most_recent_parsons(self):
    #Standard Case
    code_lines = "def foo(): #0given\nreturn 5"
    most_recent_code = "def foo():\n  return 5\n"
    expected_code_lines = "def foo(): #0given\nreturn 5 #1given"
    assert most_recent_parsons(most_recent_code, code_lines) == expected_code_lines

    #Testing diff regex placement
    code_lines = "def problem():#0given\nx = 1#1given\nx = x + 1\nreturn x"
    most_recent_code = "def problem():\n  x = x + 1\n  return x\n"
    expected_code_lines = "def problem(): #0given\nx = x + 1 #1given\nreturn x #1given\nx = 1"
    assert most_recent_parsons(most_recent_code, code_lines) == expected_code_lines

    #Moving given lines
    code_lines = "def example(): #0given\ny = 2 #1given\ny = y + 3"
    most_recent_code = "    y = 2\n  def example():\ny = y + 3\n"
    expected_code_lines = "y = 2 #2given\ndef example(): #1given\ny = y + 3 #0given"
    assert most_recent_parsons(most_recent_code, code_lines) == expected_code_lines

    #Most_recent_code not in code_lines
    code_lines = "def func(): #0given\nx = 1\nreturn x"
    most_recent_code = "def func():\n  x = 2\n  return x\n"
    with self.assertRaises(ValueError):
      most_recent_parsons(most_recent_code, code_lines)

  def test_mrp_with_blanks(self):
    #Standard Case
    code_lines = "def func(!BLANK): #0given\n!BLANK = 3\nreturn !BLANK"
    most_recent_code = "def func(num): #!ORIGINALdef func(!BLANK): #blanknum\n  x = 3 " + \
                       "#!ORIGINAL!BLANK = 3 #blankx\n  return x #!ORIGINALreturn !BLANK #blankx\n"
    expected_code_lines = "def func(!BLANK): #blanknum #0given\n!BLANK = 3 #blankx #1given" +\
                          "\nreturn !BLANK #blankx #1given"
    assert most_recent_parsons(most_recent_code, code_lines) == expected_code_lines

    #Changing value in a pre-filled blank
    code_lines = "def func(!BLANK): #0given\nx = 2\nx = x + !BLANK #1given #blank1"
    most_recent_code = "def func(num):#!ORIGINALdef func(!BLANK): #blanknum\n  x = 2\n" + \
                       "    x = x + 2#!ORIGINALx = x + !BLANK #blank2\n"
    expected_code_lines = "def func(!BLANK): #blanknum #0given\nx = 2 #1given\n" + \
                          "x = x + !BLANK #blank2 #2given"               
    assert most_recent_parsons(most_recent_code, code_lines) == expected_code_lines

    #Testing with print statements and comments in code_lines
    code_lines = "def func(x): #0given\nreturn x + 1\nprint(!BLANK)\n# !BLANK"
    most_recent_code = "def func(x):\n  # check value#!ORIGINAL# !BLANK #blankcheck value\n" + \
                       "  print(x)#!ORIGINALprint(!BLANK) #blankx\n  return x + 1\n"
    expected_code_lines = "def func(x): #0given\n# !BLANK #blankcheck value #1given\n" + \
                          "print(!BLANK) #blankx #1given\nreturn x + 1 #1given"
    assert most_recent_parsons(most_recent_code, code_lines) == expected_code_lines

if __name__ == '__main__':
  unittest.main()
