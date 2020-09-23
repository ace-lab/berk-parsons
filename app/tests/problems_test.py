# Can be run with python -m unittest app/tests/*.py
import unittest

import os
import re

from app.utils import load_config, load_config_file, problems_iter
from grader.grade import grade


class TestCase(unittest.TestCase):

  @classmethod
  def setUpClass(cls):
    cls.configs = []
    for problem_name in problems_iter():
      problem_config = load_config(problem_name)
      # Only add coding problems, not surveys or short answer.
      if type(problem_config) is dict and\
              'choices' not in problem_config and\
              'solution' in problem_config and\
              'test_cases' in problem_config and\
              'demo' not in problem_name:
        problem_config['file_name'] = problem_name
        cls.configs.append(problem_config)

  # Ensure that the sample solution passes the given test cases.
  def test_valid_solution(self):
    for problem_config in TestCase.configs:
      # print(problem_config['file_name'])
      code = problem_config['solution']
      test_fn = problem_config['test_fn']
      if 'test_code' in problem_config:
        code += problem_config['test_code']
      test_results = grade(code, problem_config['test_cases'], test_fn)
      # print(test_results)
      for test_result in test_results:
        assert(test_result['status'] == 'pass')

  # Ensure that the inital code is the same for both coding and Parsons groups.
  def test_code_parsons_start_match(self):
    # Re-implement some logic from parsons.js
    def code_lines_to_given_code(lines):
      given_indent_regex = re.compile(r"#(\d+)given\s*")
      blank_regex = re.compile(r"#blank([^#]*)")
      given_code = []
      for line in lines.split('\n'):
        if re.search(given_indent_regex, line):
          num_tabs = int(re.search(given_indent_regex, line).group(1))
          line = re.sub(given_indent_regex, '', line)
          while line.find('!BLANK') >= 0:
            blank_i = line.find('!BLANK')
            given_blank = ''
            if re.search(blank_regex, line):
              given_blank = re.search(blank_regex, line).group(1)
              line = re.sub(blank_regex, '', line)
            line = line[:blank_i] + given_blank + line[blank_i + 6:]
          given_code.append('\t' * num_tabs + line.strip())
      return '\n'.join(given_code)

    for problem_config in TestCase.configs:
      # print(problem_config['file_name'])
      parsons_starter = code_lines_to_given_code(
          problem_config['code_lines'])
      code_starter = problem_config['initial_code']
      # print("%r" % parsons_starter.replace('\n', ''))
      # print("%r" % code_starter.replace('\n', ''))
      assert parsons_starter.replace(
          '\n', '') == code_starter.replace('\n', '')

  def test_flow_problems_exist(self):
    flows_config = load_config_file('problems/flows.yaml')
    for problems in flows_config.values():
      for problem in problems:
        assert load_config(problem['problem_name'])
