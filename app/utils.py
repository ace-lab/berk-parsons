import ast
import glob
import hashlib
import os
import time
import yaml
import re

from collections import defaultdict
from pathlib import PosixPath


def load_config_file(path):
  """
  Loads a YAML file.
  Args:
      path: A path to a YAML file.

  Returns: The contents of the YAML file as a defaultdict, returning None
      for unspecified attributes.

  """
  try:
    with open(os.path.abspath(path), 'r') as file:
      config = yaml.load(file)
    if type(config) == dict:
      config = defaultdict(lambda: None, config)
    return config
  except IOError as e:
    raise Exception("Cannot find file {0}".format(path))


def load_config(problem_name):
  """
  Loads a YAML file, assuming that the YAML file is located in the problems/PROBLEM_NAME/config.yaml directory.
  Args:
      problem_name: The name of the directory in the data directory.

  Returns: The contents of the YAML file as a defaultdict, returning None
      for unspecified attributes.
  """
  config_file = os.path.join(os.path.abspath(
      "problems/"), problem_name + ".yaml")
  return load_config_file(config_file)


def retry_query(query_fn):
  """
  Given a function, tries to run it 3 (+1) times. This is to help with flaky database issues.
  """
  # TODO: Instead of a flat-out retry, this should handle rollbacks more
  # appropriately.
  for _ in range(3):
    try:
      return query_fn()
    except:
      time.sleep(1)
  return query_fn()

# Dictionary where keys are hashes computed from problem_names and values
# are problem_names
hash_dict = {}


def md5_hash(s):
  return hashlib.md5(str.encode('my_cust_string' + s)).hexdigest()


def problem_to_hash(problem_name):
  return md5_hash(problem_name)


def problems_iter():
  for problem in PosixPath('problems').glob('**/*.yaml'):
    # Remove problems/ from the path and .yaml from the filename.
    yield str(PosixPath(*problem.parts[1:]))[:-5]


def hash_to_problem(problem_hash):
  if problem_hash in hash_dict:
    return hash_dict[problem_hash]
  for problem_name in problems_iter():
    hash_dict[problem_to_hash(problem_name)] = problem_name
  return hash_dict[problem_hash]

def get_cs88_sp20_group(user_id):
  return user_id%2


def most_recent_parsons(most_recent_code, code_lines):
  recent_lines = most_recent_code.split('\n')[:-1]
  og_lines = code_lines.split('\n')
  given_regex = r'#(\d+)given\s*'
  blank_regex = r'#blank([^#]*)'
  original_regex = r'#!ORIGINAL(.*)'
  # Remove "#_given" and #blank_ in code_lines so we can find
  # each line from most_recent_code in code_lines
  for i, og_line in enumerate(og_lines):
    if re.search(given_regex, og_line):
      og_lines[i] = re.sub(given_regex, '', og_line).rstrip()
    if re.search(blank_regex, og_line):
      og_lines[i] = re.sub(blank_regex, '', og_lines[i]).rstrip()
  for i, recent_line in enumerate(recent_lines):
    split_by_tabs = recent_line.split('  ')
    num_tabs = len(split_by_tabs) - 1
    if re.search(original_regex, recent_line):
      original = re.findall(original_regex, recent_line)[0]
      index_of = og_lines.index(re.sub(blank_regex, '', original).rstrip())
      og_lines[index_of] = original
    else:
      index_of = og_lines.index(recent_line.lstrip())
    og_lines[index_of] += " #" + str(num_tabs) + "given"
    og_lines[i], og_lines[index_of] = og_lines[index_of], og_lines[i]
  return '\n'.join(og_lines)
