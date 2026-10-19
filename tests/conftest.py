import os
os.environ["MPLBACKEND"] = "agg"

import signal

import pytest
import quantity

@pytest.fixture(autouse=True)
def bundled_units(monkeypatch):
    monkeypatch.setattr(quantity, "CACHE_FILE", quantity.BUNDLED_FILE)
    quantity._cache.update(df=None,unit_data=None)


class Hang(BaseException):
    # BaseException so the interpreters' `except Exception` can't swallow it
    pass


@pytest.fixture(autouse=True)
def fail_instead_of_hanging():
    # a missing `pc += 1` in an interpreter loops forever; stop the test after 10 s instead
    if not hasattr(signal, "SIGALRM"):
        yield
        return

    def stop(signum, frame):
        raise Hang("test took over 10s probebly a infinite loop")

    old = signal.signal(signal.SIGALRM, stop)
    signal.alarm(10)
    yield
    signal.alarm(0)
    signal.signal(signal.SIGALRM, old)
