import os
import sys
import subprocess
import shutil
from pathlib import Path

def find_graphviz_executable():
    """Find the Graphviz dot executable"""
    # First check if it's in PATH
    dot_path = shutil.which('dot')
    if dot_path:
        return dot_path
    
    # Common installation locations on Windows
    common_locations = [
        "C:\\Program Files\\Graphviz\\bin\\dot.exe",
        "C:\\Program Files (x86)\\Graphviz\\bin\\dot.exe",
        os.path.expanduser("~\\Graphviz\\bin\\dot.exe"),
    ]
    
    # Check common installation locations
    for location in common_locations:
        if os.path.isfile(location):
            return location
    
    return None

def install_requirements():
    """Install required packages"""
    print("Checking and installing required packages...")
    try:
        # Check if graphviz is installed
        import graphviz
        print("Graphviz Python package is already installed.")
    except ImportError:
        print("Installing graphviz Python package...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "graphviz"])
        print("Graphviz Python package installed.")
    
    # Check for Graphviz executable
    dot_path = find_graphviz_executable()
    if dot_path:
        print(f"\nFound Graphviz executable at: {dot_path}")
        # Set environment variable for this session
        os.environ['PATH'] = os.path.dirname(dot_path) + os.pathsep + os.environ.get('PATH', '')
    else:
        print("\nWARNING: Graphviz executable (dot) not found in PATH or common locations.")
        print("This script requires the Graphviz system package to be installed.")
        print("If you haven't installed it yet, please visit: https://graphviz.org/download/")
        print("\nFor Windows users:")
        print("1. After installing Graphviz, add its bin directory to your PATH:")
        print("   - Right-click on 'This PC' or 'My Computer' and select 'Properties'")
        print("   - Click on 'Advanced system settings'")
        print("   - Click on 'Environment Variables'")
        print("   - Under 'System variables', find and select 'Path', then click 'Edit'")
        print("   - Click 'New' and add the path to the Graphviz bin directory")
        print("     (e.g., C:\\Program Files\\Graphviz\\bin)")
        print("   - Click 'OK' on all dialogs")
        print("2. Alternatively, specify the full path to the Graphviz bin directory:")
        print("   - Enter the full path to your Graphviz bin directory:")
        graphviz_path = input("   > ")
        if graphviz_path and os.path.isdir(graphviz_path):
            os.environ['PATH'] = graphviz_path + os.pathsep + os.environ.get('PATH', '')
            print(f"Added {graphviz_path} to PATH for this session.")
        else:
            print("Invalid path or no path provided.")
            print("You may need to manually set the PATH environment variable.")


def run_dependency_graph():
    """Run the dependency graph generator"""
    try:
        # Import the dependency graph module
        from dependency_graph import main as generate_graph
        
        # Configure graphviz to use the found executable
        import graphviz
        dot_path = find_graphviz_executable()
        if dot_path:
            # Set the path to the dot executable
            os.environ['PATH'] = os.path.dirname(dot_path) + os.pathsep + os.environ.get('PATH', '')
        
        print("\nGenerating dependency graph...")
        generate_graph()
        print("\nGraph generation complete!")
    except Exception as e:
        print(f"Error generating graph: {str(e)}")
        if "failed to execute" in str(e) and "dot" in str(e):
            print("\nThis error indicates that the Graphviz 'dot' executable could not be found.")
            print("Please ensure Graphviz is installed and its bin directory is in your PATH.")
            print("You can download Graphviz from: https://graphviz.org/download/")
            print("\nAfter installation, you may need to restart your computer or terminal.")


def main():
    # Get the current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Change to the visualization directory
    os.chdir(current_dir)
    
    # Install requirements
    install_requirements()
    
    # Run the dependency graph generator
    run_dependency_graph()
    
    # Provide instructions for viewing
    output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))), 
                              'data', 'visualization', 'dependency_graph.png')
    print(f"\nYou can view the dependency graph at: {output_path}")

if __name__ == '__main__':
    main()