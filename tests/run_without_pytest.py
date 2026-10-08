"""Fallback runner for environments without pytest: python tests/run_without_pytest.py [test_engine] [test_backend]"""
import contextlib, importlib, sys, time, traceback, types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
try:
    import pytest  # noqa: F401
except ImportError:
    stub = types.ModuleType("pytest")

    class _Info:
        value = None

    @contextlib.contextmanager
    def raises(exc):
        info = _Info()
        try:
            yield info
        except exc as e:
            info.value = e
            return
        raise AssertionError(f"did not raise {exc}")
    stub.raises = raises
    sys.modules["pytest"] = stub

sys.path.insert(0, str(Path(__file__).parent))
failed = 0
for modname in (sys.argv[1:] or ["test_engine", "test_backend"]):
    mod = importlib.import_module(modname)
    for name in sorted(n for n in dir(mod) if n.startswith("test_")):
        t = time.time()
        try:
            getattr(mod, name)()
            print(f"PASS {modname}.{name} ({time.time()-t:.1f}s)")
        except Exception:
            failed += 1
            print(f"FAIL {modname}.{name}"); traceback.print_exc()
sys.exit(1 if failed else 0)
