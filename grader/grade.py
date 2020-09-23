from .tester import Tester


def grade(code, tests, function_name):
  """
  Tests the code
  Parameters:
      code (str): A string containing student submitted code
      tests (list of lists): Contains the tests to be run using the code. Each list's first value should be another
      list containing the desired inputs, and the second value should be the expected output. For example, to run
      the tests add_up(1, [1, 2, 3]) with expected output False and the test add_up(3, [1, 2, 3]) with expected
      output True, the input should look like [[[1, [1, 2, 3]], False], [[3, [1, 2, 3]], True]]
      function_name (str): The function name to be tested. If function_name is None, the tester will automatically
      run the tests on the first defined function.
  Returns:
      list of dictionaries, one dictionary for every test containing the results.
  """
  tester = Tester(code, tests, function_name)
  tester.test()
  results = tester.get_results()
  return results
