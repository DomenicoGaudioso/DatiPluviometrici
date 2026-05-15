from __future__ import annotations

import importlib.util
import json
import math
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_src():
    spec = importlib.util.spec_from_file_location("pluvio_src", ROOT / "src.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def assert_close(name: str, actual: float, expected: float, tol: float) -> None:
    if math.isnan(actual) or abs(actual - expected) > tol:
        raise AssertionError(f"{name}: actual={actual!r}, expected={expected!r}, tol={tol}")


def main() -> None:
    src = load_src()
    bench = json.loads((ROOT / "test" / "benchmark" / "base.json").read_text(encoding="utf-8"))
    h = src.tirante_trapezoidale_bisezione(**bench["hydraulic_input"])
    series = {float(k): v for k, v in bench["gumbel_series"].items()}
    cpp = src.cpp_gumbel([1.0, 3.0, 6.0, 12.0, 24.0], series, 50.0)
    actual = {
        "tirante_m": h["tirante_m"],
        "area_m2": h["area_m2"],
        "velocita_ms": h["velocita_ms"],
        "gumbel_h_1h_tr50": cpp["altezze_mm"][0],
        "cpp_a_tr50": cpp["a"],
        "cpp_n_tr50": cpp["n"],
        "cpp_r2_tr50": cpp["r2"],
    }
    tol = float(bench["abs_tolerance"])
    for key, expected in bench["expected"].items():
        assert_close(key, float(actual[key]), float(expected), tol)
    print("OK DatiPluviometrici benchmark: base")


if __name__ == "__main__":
    main()
