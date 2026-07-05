# custom/dd-seo-audit/tests/conftest.py
import os
import sys

SCRIPTS = os.path.join(os.path.dirname(__file__), "..", "skills", "dd-seo", "scripts")
sys.path.insert(0, os.path.abspath(SCRIPTS))
