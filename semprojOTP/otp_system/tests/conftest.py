"""Keep the test run away from the real encrypted device store."""
import os
import tempfile

os.environ.setdefault("WALK_OTP_STORE_PATH", os.path.join(tempfile.mkdtemp(prefix="walk_otp_test_"), "store.json.enc"))
