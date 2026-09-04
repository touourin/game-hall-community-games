from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

TEST_ROOT = Path(__file__).resolve().parent
if str(TEST_ROOT) not in sys.path:
    sys.path.insert(0, str(TEST_ROOT))

# Community plugins are collected together with ``--import-mode=importlib``.
# Give this helper module a plugin-specific name so it cannot collide with
# another plugin's top-level ``tests`` package.
HELPER_NAME = "splendor_test_helpers"
if HELPER_NAME not in sys.modules:
    helper_path = Path(__file__).resolve().parent / "helpers.py"
    helper_spec = importlib.util.spec_from_file_location(HELPER_NAME, helper_path)
    if helper_spec is None or helper_spec.loader is None:
        raise RuntimeError("cannot load Splendor test helpers")
    helper_module = importlib.util.module_from_spec(helper_spec)
    sys.modules[HELPER_NAME] = helper_module
    helper_spec.loader.exec_module(helper_module)
