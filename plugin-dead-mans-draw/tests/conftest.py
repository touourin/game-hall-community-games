from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


HELPER_MODULE = "dead_mans_draw_test_helpers"
HELPER_PATH = Path(__file__).with_name("helpers.py")
HARNESS_MODULE = "dead_mans_draw_live_browser_harness"
HARNESS_PATH = Path(__file__).with_name("live_browser_harness") / "server.py"


def load_module(name: str, path: Path) -> None:
    if name in sys.modules:
        return
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load Dead Man's Draw test module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)


load_module(HELPER_MODULE, HELPER_PATH)
load_module(HARNESS_MODULE, HARNESS_PATH)
