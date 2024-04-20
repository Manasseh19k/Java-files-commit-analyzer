import unittest
from unittest.mock import patch, MagicMock
from GitAnalyzer import TestAnalyzer

class TestTestAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = TestAnalyzer("commit_sha", "project_name")

    @patch('os.path.exists')
    @patch('os.listdir')
    def test_clone_repository_new_repo(self, mock_listdir, mock_exists):
        mock_exists.return_value = False
        mock_listdir.return_value = False
        with patch.object(Repo, 'clone_from') as mock_clone_from:
            self.analyzer.clone_repository()
            mock_clone_from.assert_called_once_with("https://github.com/project_name.git", "project_name_repo")

    @patch('os.path.exists')
    @patch('os.listdir')
    def test_clone_repository_existing_repo(self, mock_listdir, mock_exists):
        mock_exists.return_value = True
        mock_listdir.return_value = True
        with patch.object(Repo, '__init__') as mock_repo_init:
            mock_repo_init.return_value = None
            self.analyzer.clone_repository()
            mock_repo_init.assert_called_once_with("project_name_repo")

    def test_identify_test_file_not_found(self):
        self.analyzer.repo = MagicMock()
        commit = MagicMock()
        blob = MagicMock()
        blob.path = "NotATest.java"
        commit.tree.traverse.return_value = [blob]
        self.analyzer.repo.commit.return_value = commit
        self.assertIsNone(self.analyzer.identify_test_file("test_name"))

    def test_identify_test_file_found(self):
        self.analyzer.repo = MagicMock()
        commit = MagicMock()
        blob = MagicMock()
        blob.path = "ATest.java"
        blob.data_stream.read.return_value = b"test_name"
        commit.tree.traverse.return_value = [blob]
        self.analyzer.repo.commit.return_value = commit
        self.assertEqual(self.analyzer.identify_test_file("test_name"), "ATest.java")

    def test_populate_variable_class_map(self):
        tree = MagicMock()
        field_declaration = MagicMock()
        field_declaration.type.name = "ClassType"
        field_declaration.declarators = [MagicMock(name="VariableName")]
        tree.filter.return_value = [(None, field_declaration)]
        self.assertEqual(self.analyzer.populate_variable_class_map(tree), {"VariableName": "ClassType"})

    def test_map_internal_methods(self):
        tree = MagicMock()
        method_declaration = MagicMock()
        method_declaration.name = "MethodName"
        tree.filter.return_value = [(None, method_declaration)]
        self.assertEqual(self.analyzer.map_internal_methods(tree), {"MethodName": method_declaration})

    def test_parse_imports(self):
        tree = MagicMock()
        import_declaration = MagicMock()
        import_declaration.path = "com.example.ClassName"
        tree.imports = [import_declaration]
        self.assertEqual(self.analyzer.parse_imports(tree), {"ClassName": "com.example.ClassName"})

if __name__ == '__main__':
    unittest.main()