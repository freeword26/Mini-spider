"""Pytest configuration for spider_meta tests."""
import os, sys
# conftest is at <repo_root>/spider_meta/tests/conftest.py
# We need <repo_root> on sys.path so `import spider_meta` resolves
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)
