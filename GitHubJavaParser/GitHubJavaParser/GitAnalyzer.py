import os
import csv
from git import Repo
import javalang


class TestAnalyzer:
    def __init__(self, parent_commit_sha, project_name):
        self.parent_commit_sha = parent_commit_sha
        self.project_name = project_name
        self.local_repo_path = f"{project_name}_repo"
        self.repo = None
        self.reserved_words = ['assertEquals', 'fail', 'assertTrue', 'assertFalse', 'assertNull', 'assertThat',
                               'assertThrows', 'assertNumberOfNodes', 'assertNotNull', 'assertSame']

    def clone_repository(self):
        if not os.path.exists(self.local_repo_path) or not os.listdir(self.local_repo_path):
            self.repo = Repo.clone_from(f"https://github.com/{self.project_name}.git", self.local_repo_path)
        else:
            self.repo = Repo(self.local_repo_path)

    def identify_test_file(self, redundant_test_name):
        commit = self.repo.commit(self.parent_commit_sha)
        for blob in commit.tree.traverse():
            if blob.path.endswith("Test.java"):
                test_file_content = blob.data_stream.read().decode('utf-8')
                if redundant_test_name in test_file_content:
                    return blob.path
        return None

    def identify_commit_and_extract_function_calls(self, redundant_test_file_content, redundant_test_name):
        commit = self.repo.commit(self.parent_commit_sha)
        test_case_link = f"https://github.com/{self.project_name}/blob/{self.parent_commit_sha}/{redundant_test_file_content}"
        tree = javalang.parse.parse(self.repo.git.show(f"{self.parent_commit_sha}:{redundant_test_file_content}"))

        # Store the package name
        self.package_name = tree.package.name if tree.package else ""

        variable_class_map = self.populate_variable_class_map(tree)
        internal_methods_map = self.map_internal_methods(tree)
        class_methods_map = {}
        class_import_map = self.parse_imports(tree)

        self.analyze_method_calls(tree, redundant_test_name, class_methods_map, variable_class_map,
                                  internal_methods_map, class_import_map)

        return test_case_link, class_methods_map, redundant_test_name

    def populate_variable_class_map(self, tree):
        variable_class_map = {}
        for _, node in tree.filter(javalang.tree.FieldDeclaration):
            class_type = node.type.name
            for declarator in node.declarators:
                variable_name = declarator.name
                variable_class_map[variable_name] = class_type

        for _, node in tree.filter(javalang.tree.LocalVariableDeclaration):
            class_type = node.type.name
            for declarator in node.declarators:
                variable_name = declarator.name
                if isinstance(declarator.initializer, javalang.tree.ClassCreator):
                    right_class_type = declarator.initializer.type.name
                    if class_type != right_class_type:
                        variable_class_map[variable_name] = (class_type, right_class_type)
                    else:
                        variable_class_map[variable_name] = class_type
                else:
                    variable_class_map[variable_name] = class_type

        for _, node in tree.filter(javalang.tree.FormalParameter):
            class_type = node.type.name
            variable_name = node.name
            variable_class_map[variable_name] = class_type

        return variable_class_map

    def map_internal_methods(self, tree):
        internal_methods_map = {}
        for _, node in tree.filter(javalang.tree.MethodDeclaration):
            method_name = node.name
            internal_methods_map[method_name] = node
        return internal_methods_map

    def analyze_method_calls(self, tree, method_name, class_methods_map, variable_class_map, internal_methods_map,
                             class_import_map):
        method_node = next(
            (node for _, node in tree.filter(javalang.tree.MethodDeclaration) if node.name == method_name), None)
        if method_node:
            self.process_method_body(method_node, class_methods_map, variable_class_map, internal_methods_map,
                                     class_import_map)

    def process_method_body(self, method_node, class_methods_map, variable_class_map, internal_methods_map,
                            class_import_map):
        for _, invocation_node in method_node.filter(javalang.tree.MethodInvocation):
            self.process_method_invocation(invocation_node, class_methods_map, variable_class_map, internal_methods_map,
                                           class_import_map)

    def parse_imports(self, tree):
        class_import_map = {}
        for import_declaration in tree.imports:
            class_name = import_declaration.path.split('.')[-1]
            class_import_map[class_name] = import_declaration.path
        return class_import_map

    def process_method_invocation(self, node, class_methods_map, variable_class_map, internal_methods_map,
                                  class_import_map):
        # Check if the method call is a jUnit method or its qualifier starts with 'java' or 'javax'
        if node.member in self.reserved_words or (
                node.qualifier and (node.qualifier.startswith('java') or node.qualifier.startswith('javax'))):
            return  # Skip this method invocation

        if node.qualifier:
            if node.qualifier in variable_class_map:
                class_name = variable_class_map[node.qualifier]
                # If the class name is a tuple, it means the variable was assigned an instance of a class
                # Use the class of the instance instead of the declared type of the variable
                if isinstance(class_name, tuple):
                    class_name = class_name[1]
            else:
                class_name = node.qualifier
        else:
            class_name = "Internal/External"

        method_calls = class_methods_map.get(class_name, set())
        # Append the package name, class name, and method name to get the fully qualified method name
        # Exclude the parameters from the method call
        # Use the correct package name for the class
        if class_name in class_import_map:
            method_calls.add(f"{class_import_map[class_name]}.{node.member}()")
        else:
            method_calls.add(f"{self.package_name}.{class_name}.{node.member}()")
        class_methods_map[class_name] = method_calls

        # Recursively analyze internal method invocations
        if node.member in internal_methods_map:
            internal_method_node = internal_methods_map[node.member]
            self.process_method_body(internal_method_node, class_methods_map, variable_class_map, internal_methods_map,
                                     class_import_map)

    def extract_method_chain(self, node, chain=None):
        if chain is None:
            chain = []

        if isinstance(node, javalang.tree.MethodInvocation):
            chain.insert(0, node.member)
            if isinstance(node.qualifier, javalang.tree.MethodInvocation):
                self.extract_method_chain(node.qualifier, chain)

        return chain

    def process_constructor(self, tree):
        constructors = []
        for _, node in tree.filter(javalang.tree.ConstructorDeclaration):
            constructors.append(node)
        return constructors if constructors else ["No constructors found."]

    def analyze_tests(self, redundant_test_names):
        self.clone_repository()
        results = []
        if not self.repo:
            print("Failed to access repository.")
            return results

        for redundant_test_name in redundant_test_names:
            test_file_path = self.identify_test_file(redundant_test_name)
            if test_file_path:
                test_case_link, class_method_mappings, _ = self.identify_commit_and_extract_function_calls(
                    test_file_path, redundant_test_name)
                tree = javalang.parse.parse(self.repo.git.show(f"{self.parent_commit_sha}:{test_file_path}"))
                constructors = self.process_constructor(tree)
                if class_method_mappings:
                    for class_name, method_calls in class_method_mappings.items():
                        results.append({
                            'Test Case Link': test_case_link,
                            'Class Name': class_name,
                            'Method Calls': ', '.join(method_calls) if method_calls else "No method calls",
                            'Constructors': ','.join(constructors),
                            'Redundant Test Name': redundant_test_name,
                            'Commit SHA': self.parent_commit_sha
                        })
                else:
                    # Append a result with class names but no method calls if possible
                    results.append({
                        'Test Case Link': test_case_link,
                        'Class Name': "Classes identified, no method calls",
                        'Method Calls': '',
                        'Redundant Test Name': redundant_test_name,
                        'Commit SHA': self.parent_commit_sha
                    })
            else:
                print(f"Test file not found for {redundant_test_name}.")
        return results

    def write_to_csv(self, results, output_csv):
        with open(output_csv, mode='w', newline='', encoding='utf-8') as csv_file:
            fieldnames = ['Test Case Link', 'Class Name', 'Method Calls', 'Constructors', 'Redundant Test Name', 'Commit SHA']
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            for result in results:
                writer.writerow(result)


# Example usage
parent_commit_sha = "71bfa2daeb01fdaab7c35047d04e06af0ef10461"
project_name = "apache/commons-math"
redundant_test_names = ['testAlphaRangeBelowZero']
output_csv = "redundant_tests_without_class_column.csv"

analyzer = TestAnalyzer(parent_commit_sha, project_name)
results = analyzer.analyze_tests(redundant_test_names)
analyzer.write_to_csv(results, output_csv)