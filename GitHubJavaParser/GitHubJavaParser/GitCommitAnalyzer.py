import csv
from pydriller import Repository
import javalang

# Constants
GITHUB_BASE_URL = 'https://github.com/'
PROJECT_NAME = 'apache/commons-lang'
LOCAL_PATH = 'local_repo'
CLASS_NAME = 'MyClass'
METHOD_NAMES = ['methodName1', 'methodName2']


# Parse Java methods from content
def parse_methods(content):
    try:
        tree = javalang.parse.parse(content)
        methods = {}
        for _, class_decl in tree.filter(javalang.tree.ClassDeclaration):
            for method in class_decl.methods:
                methods[method.name] = method
        return methods
    except javalang.parser.JavaSyntaxError:
        return {}


# Analyze modifications in the specified methods
def analyze_methods(repo_url, class_name, method_names):
    results = []
    for commit in Repository(path_to_repo=repo_url, only_modifications_with_file_types=['.java']).traverse_commits():
        for mod in commit.modifications:
            if mod.filename.endswith('.java') and class_name in mod.source_code:
                old_methods = parse_methods(mod.source_code_before or "")
                new_methods = parse_methods(mod.source_code or "")
                for method_name in method_names:
                    old_method = old_methods.get(method_name)
                    new_method = new_methods.get(method_name)
                    if old_method and new_method and old_method != new_method:
                        commit_url = f"https://github.com/{PROJECT_NAME}/commit/{commit.hash}"
                        results.append({
                            'file_path': mod.new_path,
                            'commit_sha': commit_url,
                            'method_before': str(old_method),
                            'method_after': str(new_method)
                        })
    return results


# Save results to CSV
def save_results(results, filename):
    with open(filename, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['File Path', 'Commit URL', 'Method Name', 'Method Before', 'Method After'])
        for result in results:
            # Format commit URL as a clickable hyperlink
            hyperlink = f'=HYPERLINK("{result["commit_url"]}", "View Commit")'
            writer.writerow([
                result['file_path'],
                hyperlink,
                result['method_name'],
                result['method_before'],
                result['method_after']
            ])


# Main execution
repo_url = GITHUB_BASE_URL + PROJECT_NAME
results = analyze_methods(repo_url, CLASS_NAME, METHOD_NAMES)
save_results(results, 'method_changes.csv')
