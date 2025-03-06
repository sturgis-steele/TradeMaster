import os
import ast
import graphviz
from typing import Dict, Set, List

def parse_imports(file_path: str) -> Set[str]:
    """Parse Python file and extract its imports"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())
    except:
        return set()
    
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                imports.add(name.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)
    return imports

def find_python_files(start_path: str) -> List[str]:
    """Find all Python files in the project"""
    python_files = []
    for root, _, files in os.walk(start_path):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    return python_files

def create_dependency_graph(project_path: str, output_file: str = 'dependency_graph'):
    """Create a visual graph of project dependencies"""
    # Initialize graph
    dot = graphviz.Digraph('Project Dependencies')
    dot.attr(rankdir='LR')
    
    # Find all Python files
    python_files = find_python_files(project_path)
    
    # Create nodes and edges
    for file_path in python_files:
        # Create node name from relative path
        rel_path = os.path.relpath(file_path, project_path)
        node_name = rel_path.replace('\\', '/')
        
        # Add node
        dot.node(node_name, node_name)
        
        # Parse imports
        imports = parse_imports(file_path)
        
        # Add edges for each import
        for imp in imports:
            # Convert import to potential file path
            imp_parts = imp.split('.')
            for i in range(len(imp_parts)):
                potential_path = os.path.join(project_path, *imp_parts[:i+1])
                potential_file = f"{potential_path}.py"
                if potential_file in python_files:
                    rel_imp_path = os.path.relpath(potential_file, project_path)
                    dot.edge(node_name, rel_imp_path.replace('\\', '/'))
                    break
    
    # Save the graph
    dot.render(output_file, format='png', cleanup=True)

def main():
    # Get the project root path
    project_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Create the visualization
    output_path = os.path.join(project_path, 'data', 'visualization', 'dependency_graph')
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    create_dependency_graph(project_path, output_path)
    print(f"Dependency graph has been created at: {output_path}.png")

if __name__ == '__main__':
    main()