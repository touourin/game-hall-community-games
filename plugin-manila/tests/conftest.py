from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1] / "backend"
PACKAGE_NAME = "manila_plugin_test_backend"

if PACKAGE_NAME not in sys.modules:
    package = types.ModuleType(PACKAGE_NAME)
    package.__path__ = [str(BACKEND_ROOT)]
    package.__package__ = PACKAGE_NAME
    sys.modules[PACKAGE_NAME] = package


def load_module(name: str) -> None:
    qualified = f"{PACKAGE_NAME}.{name}"
    if qualified in sys.modules:
        return
    spec = importlib.util.spec_from_file_location(qualified, BACKEND_ROOT / f"{name}.py")
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load Manila module {name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[qualified] = module
    spec.loader.exec_module(module)


for module_name in ("catalog", "state", "rules", "projection", "engine"):
    load_module(module_name)

