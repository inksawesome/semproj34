"""
Test isolation: a throw-away database, no saved captures, project root as cwd.
Runs before any test module imports database.py.
"""
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "semprojOTP", "otp_system"))
os.chdir(ROOT)

os.environ["VT_DB_PATH"] = os.path.join(tempfile.mkdtemp(prefix="vaulttrust_test_"), "test.db")
os.environ["VT_SAVE_CAPTURES"] = "0"
