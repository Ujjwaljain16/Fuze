"""
Fuze Backend Package
Adds backend directory to Python path for imports
"""
import os
import sys

# Add backend directory to Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

