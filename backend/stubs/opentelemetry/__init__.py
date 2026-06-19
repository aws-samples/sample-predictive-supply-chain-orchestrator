"""
Opentelemetry stub for AWS Lambda.

Strands SDK imports opentelemetry but the real package has binary deps
that conflict between aarch64 (AgentCore) and x86_64 (Lambda).
This stub auto-provides any opentelemetry.* sub-module as a no-op.
"""
import sys
import types


class _Noop:
    """Universal no-op: callable, iterable, context manager, subscriptable, unionable."""
    def __init__(self, *a, **kw): pass
    def __call__(self, *a, **kw): return _Noop()
    def __getattr__(self, name): return _Noop()
    def __enter__(self): return self
    def __exit__(self, *a): pass
    def __iter__(self): return iter([])
    def __bool__(self): return False
    def __str__(self): return ""
    def __repr__(self): return "Noop()"
    def __or__(self, other): return self
    def __ror__(self, other): return self
    def __class_getitem__(cls, item): return cls
    def __getitem__(self, item): return _Noop()
    def __eq__(self, other): return False
    def __hash__(self): return 0
    def __len__(self): return 0


class _OtelStubModule(types.ModuleType):
    """Module that returns _Noop for any attribute access."""
    def __getattr__(self, name):
        return _Noop()


class _OtelStubFinder:
    def find_module(self, fullname, path=None):
        if fullname.startswith("opentelemetry"):
            return self
        return None

    def load_module(self, fullname):
        if fullname in sys.modules:
            return sys.modules[fullname]
        mod = _OtelStubModule(fullname)
        mod.__path__ = []
        mod.__loader__ = self
        mod.__package__ = fullname
        sys.modules[fullname] = mod
        return mod


sys.meta_path.insert(0, _OtelStubFinder())
