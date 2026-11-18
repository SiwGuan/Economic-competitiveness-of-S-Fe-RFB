"""Source-integrity, numerical-parity and command-line integration checks."""
import ast
import hashlib
import inspect
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import run_tea
import tea_model


def reference_namespace():
    """Load only literal assignments and functions from the archived source."""
    tree = ast.parse((ROOT / "original/Fe-SRFB TEA.py").read_text(encoding="utf-8-sig"))
    nodes = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            nodes.append(node)
        elif isinstance(node, ast.Assign):
            try:
                ast.literal_eval(node.value)
            except (ValueError, TypeError):
                continue
            nodes.append(node)
    namespace = {}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "archived_reference", "exec"), namespace)
    return namespace


def reference_result(p):
    ref = reference_namespace()
    ref.update(p)
    ce, cp, area = ref["electrolyte_energy_cost"](**{key: p[key] for key in inspect.signature(ref["electrolyte_energy_cost"]).parameters})
    capital = ref["calculate_system_cost"](ce, cp, p["E_b_nom"], p["P_b_nom"])
    equity, loans = ref["financing_model"](capital, p["f_d"], p["d_r"], p["N_y"], p["r_d_y"])
    replacement = ref["lcos_replacement_cost"](p["P_b_nom"], p["n_rep_P"], p["r_d_y"], p["t_rep_P"], p["c_m"], p["c_felt"], area)
    inputs = dict(p, Pb_nom=p["P_b_nom"])
    terms = ref["calculate_discharged_energy_cost"](**{key: inputs[key] for key in inspect.signature(ref["calculate_discharged_energy_cost"]).parameters})
    net, total = ref["levelized_cost"](equity, loans, replacement, *terms, r_i_y=p["r_i_y"], c_el=p["c_el"])
    return capital / p["E_b_nom"], total * 1000, sum(terms[-1])


class ReproductionTests(unittest.TestCase):
    def test_original_integrity_and_function_identity(self):
        manifest = json.loads((ROOT / "SOURCE_PROVENANCE.json").read_text(encoding="utf-8"))
        archived = (ROOT / manifest["source_file"]).read_bytes()
        self.assertEqual(hashlib.sha256(archived).hexdigest(), manifest["source_sha256"])
        original = {n.name: n for n in ast.parse(archived.decode("utf-8-sig")).body if isinstance(n, ast.FunctionDef)}
        portable = {n.name: n for n in ast.parse((ROOT / "tea_model.py").read_text(encoding="utf-8")).body if isinstance(n, ast.FunctionDef)}
        self.assertEqual(set(portable), set(manifest["equation_functions"]))
        for name, node in portable.items():
            self.assertEqual(ast.dump(node), ast.dump(original[name]), name)

    def test_three_configurations_against_original(self):
        golden = {
            "baseline_4h": (349.1034333257177, 344.42551658809595, 26266462.9872),
            "baseline_8h": (220.50729372484935, 291.2344846083629, 52532925.9744),
            "source_defaults": (153.4234598040583, 265.98225202257663, 52532925.9744),
        }
        for name, expected in golden.items():
            with self.subTest(config=name):
                p = run_tea.load_parameters(ROOT / "configs" / f"{name}.json")
                summary, _ = run_tea.calculate(p)
                actual = tuple(summary[k] for k in ["capital_cost_EUR_per_kWh", "LCOS_EUR_per_MWh", "lifetime_delivered_energy_kWh"])
                self.assertEqual(actual, reference_result(p))
                for value, target in zip(actual, expected):
                    self.assertAlmostEqual(value, target, places=8)

    def test_overrides_reach_global_and_default_arguments(self):
        p = run_tea.load_parameters(ROOT / "configs/baseline_4h.json")
        p.update(c_pumps=p["c_pumps"] * 1.2, c_el=0.2, r_i_y=0.02)
        result, _ = run_tea.calculate(p)
        expected = reference_result(p)
        self.assertEqual(result["capital_cost_EUR_per_kWh"], expected[0])
        self.assertEqual(result["LCOS_EUR_per_MWh"], expected[1])

    def test_parameter_guards(self):
        p = run_tea.load_parameters(ROOT / "configs/baseline_4h.json")
        with self.assertRaisesRegex(ValueError, "must agree"):
            run_tea.calculate(dict(p, DOD_max=0.7))
        with self.assertRaisesRegex(ValueError, "discharge voltage"):
            run_tea.calculate(dict(p, OCV=0.01))
        with self.assertRaisesRegex(ValueError, "eta_rt"):
            run_tea.calculate(dict(p, eta_rt=0))

    def test_cli_exports_and_prevents_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "example"
            command = [sys.executable, str(ROOT / "run_tea.py"), "--config", str(ROOT / "configs/baseline_4h.json"), "--output", str(output), "--daily", "--sweep", "eta_rt", "--start", "0.75", "--stop", "0.9", "--points", "3"]
            process = subprocess.run(command, text=True, capture_output=True)
            self.assertEqual(process.returncode, 0, process.stderr)
            for name in ["summary.json", "summary.csv", "parameters.json", "daily_output.csv", "sensitivity.csv"]:
                self.assertTrue((output / name).is_file(), name)
            before = (output / "summary.json").read_bytes()
            rerun = subprocess.run(command, text=True, capture_output=True)
            self.assertNotEqual(rerun.returncode, 0)
            self.assertEqual(before, (output / "summary.json").read_bytes())


if __name__ == "__main__":
    unittest.main()
