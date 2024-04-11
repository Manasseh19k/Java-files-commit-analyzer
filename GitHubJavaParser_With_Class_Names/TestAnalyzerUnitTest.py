import unittest
from unittest import mock
from TestAnalyzer import TestAnalyzer


class TestTestAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = TestAnalyzer("3f261441651fe6a5f57cf4e6aa655f9661dc606a", "google/gson")

    @mock.patch('os.path.exists')
    @mock.patch('os.listdir')
    @mock.patch('git.Repo.clone_from')
    def test_clone_repository_new(self, mock_clone_from, mock_listdir, mock_exists):
        mock_exists.return_value = False
        mock_listdir.return_value = False
        self.analyzer.clone_repository()
        mock_clone_from.assert_called_once()

    @mock.patch('os.path.exists')
    @mock.patch('os.listdir')
    @mock.patch('git.Repo')
    def test_clone_repository_existing(self, mock_repo, mock_listdir, mock_exists):
        mock_exists.return_value = True
        mock_listdir.return_value = True
        self.analyzer.clone_repository()
        mock_repo.assert_called_once()

    @mock.patch('javalang.parse.parse')
    def test_populate_variable_class_map(self, mock_parse):
        mock_parse.return_value = mock.MagicMock()
        self.analyzer.populate_variable_class_map(mock_parse.return_value)
        self.assertEqual(len(mock_parse.return_value.filter.call_args_list), 2)

    @mock.patch('javalang.parse.parse')
    def test_map_internal_methods(self, mock_parse):
        mock_parse.return_value = mock.MagicMock()
        self.analyzer.map_internal_methods(mock_parse.return_value)
        mock_parse.return_value.filter.assert_called_once()

    @mock.patch('javalang.parse.parse')
    def test_analyze_method_calls(self, mock_parse):
        mock_parse.return_value = mock.MagicMock()
        self.analyzer.analyze_method_calls(mock_parse.return_value, 'testMethod', {}, {}, {})
        mock_parse.return_value.filter.assert_called_once()

    @mock.patch('javalang.parse.parse')
    def test_process_method_body(self, mock_parse):
        mock_parse.return_value = mock.MagicMock()
        self.analyzer.process_method_body(mock_parse.return_value, {}, {}, {})
        mock_parse.return_value.filter.assert_called_once()

    @mock.patch('javalang.tree.MethodInvocation')
    def test_process_method_invocation(self, mock_method_invocation):
        mock_method_invocation.member = 'testMethod'
        mock_method_invocation.qualifier = 'testQualifier'
        self.analyzer.process_method_invocation(mock_method_invocation, {}, {'testQualifier': 'TestClass'}, {})
        self.assertEqual(len(mock_method_invocation.filter.call_args_list), 1)

    @mock.patch('javalang.tree.MethodInvocation')
    def test_extract_method_chain(self, mock_method_invocation):
        mock_method_invocation.member = 'testMethod'
        mock_method_invocation.qualifier = mock.MagicMock()
        self.analyzer.extract_method_chain(mock_method_invocation)
        self.assertEqual(len(mock_method_invocation.filter.call_args_list), 1)


if __name__ == '__main__':
    unittest.main()
