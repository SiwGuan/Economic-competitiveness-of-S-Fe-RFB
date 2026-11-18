"""Run the supplied S-Fe TEA equations with explicit scenario inputs."""
import argparse
import csv
import inspect
import json
import math
from pathlib import Path

import tea_model as model

ROOT = Path(__file__).resolve().parent


def load_parameters(config):
    defaults = json.loads((ROOT / "configs/source_defaults.json").read_text(encoding="utf-8"))
    supplied = json.loads(Path(config).read_text(encoding="utf-8"))
    unknown = set(supplied) - set(defaults)
    if unknown:
        raise ValueError(f"Unknown parameters: {sorted(unknown)}")
    defaults.update(supplied)
    return defaults


def validate(p):
    for key, value in p.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"{key} must be a finite number")
    if p["DoD_max"] != p["DOD_max"]:
        raise ValueError("DoD_max and DOD_max must agree; both names occur in the original equations.")
    for key in ["eta_rt", "eta_sys_d", "DoD_max", "cap_lim"]:
        if not 0 < p[key] <= 1:
            raise ValueError(f"{key} must be in (0, 1]")
    for key in ["P_b_nom", "E_b_nom", "N_y", "N", "i_d", "OCV", "d_r", "F", "n_e_minus", "cyc_day", "t_rep_P", "conc_act_anode", "conc_act_catholyte", "MW_active_anode", "MW_active_Catholyte"]:
        if p[key] <= 0:
            raise ValueError(f"{key} must be positive")
    for key in ["N_y", "N", "n_rep_P"]:
        if not isinstance(p[key], int):
            raise ValueError(f"{key} must be an integer")
    if p["n_rep_P"] < 0 or p["r_i_y"] <= -1 or p["r_d_y"] <= -1 or not 0 <= p["f_d"] <= 1:
        raise ValueError("Invalid replacement count, rate or debt fraction")
    for key in ["r_CO", "r_ED", "r_time", "ASR"]:
        if p[key] < 0:
            raise ValueError(f"{key} must be non-negative")
    if p["OCV"] - p["i_d"] * p["ASR"] * 1e-3 <= 0:
        raise ValueError("The source model requires positive discharge voltage.")
    if p["rho_el_anode"] <= p["conc_act_anode"] * p["MW_active_anode"]:
        raise ValueError("Anolyte supporting-electrolyte mass must be positive")
    if p["rho_el_catholyte"] <= p["conc_act_catholyte"] * p["MW_active_Catholyte"]:
        raise ValueError("Catholyte supporting-electrolyte mass must be positive")


def calculate(p):
    """Use the original equations and return scalars plus lifetime time series."""
    validate(p)
    # Original functions use several global component costs. Bind all supplied
    # scalar values explicitly so a configuration change affects those terms too.
    for key, value in p.items():
        setattr(model, key, value)
    energy_cost, power_cost, area = model.electrolyte_energy_cost(
        **{k: p[k] for k in inspect.signature(model.electrolyte_energy_cost).parameters}
    )
    capital = model.calculate_system_cost(energy_cost, power_cost, p["E_b_nom"], p["P_b_nom"])
    equity, loans = model.financing_model(capital, p["f_d"], p["d_r"], p["N_y"], p["r_d_y"])
    replacement = model.lcos_replacement_cost(p["P_b_nom"], p["n_rep_P"], p["r_d_y"], p["t_rep_P"], p["c_m"], p["c_felt"], area)
    operating = dict(p, Pb_nom=p["P_b_nom"])
    terms = model.calculate_discharged_energy_cost(
        **{k: operating[k] for k in inspect.signature(model.calculate_discharged_energy_cost).parameters}
    )
    net, lcos = model.levelized_cost(equity, loans, replacement, *terms, r_i_y=p["r_i_y"], c_el=p["c_el"])
    fixed, variable, lost_energy, discounted_output, output = terms
    summary = {
        "power_kW": p["P_b_nom"],
        "energy_kWh": p["E_b_nom"],
        "duration_h": p["E_b_nom"] / p["P_b_nom"],
        "OCV_V": p["OCV"],
        "eta_rt": p["eta_rt"],
        "energy_related_cost_EUR_per_kWh": energy_cost,
        "power_related_cost_EUR_per_kW": power_cost,
        "active_area_m2_per_kW": area,
        "capital_cost_EUR": capital,
        "capital_cost_EUR_per_kWh": capital / p["E_b_nom"],
        "LCOS_net_EUR_per_MWh": net * 1000,
        "LCOS_EUR_per_MWh": lcos * 1000,
        "lifetime_delivered_energy_kWh": sum(output),
        "discounted_lifetime_delivered_energy_kWh": sum(discounted_output),
        "equity_present_value_EUR": equity,
        "debt_payments_present_value_EUR": sum(loans),
        "replacement_present_value_EUR": replacement,
        "fixed_OM_present_value_EUR": sum(fixed),
        "variable_OM_present_value_EUR": sum(variable),
        "charging_loss_cost_present_value_EUR": sum(lost_energy),
    }
    if not all(math.isfinite(x) for x in summary.values()):
        raise ValueError("The requested scenario produced a non-finite result")
    return summary, terms


def write_csv(path, rows):
    if not rows:
        raise ValueError("Cannot write an empty CSV")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/baseline_4h.json")
    parser.add_argument("--output", type=Path, default=ROOT / "results/baseline_4h")
    parser.add_argument("--daily", action="store_true", help="Export daily delivered energy and charging-loss costs")
    parser.add_argument("--sweep", help="Parameter name for a one-at-a-time sensitivity scan")
    parser.add_argument("--start", type=float)
    parser.add_argument("--stop", type=float)
    parser.add_argument("--points", type=int, default=100)
    args = parser.parse_args()
    p = load_parameters(args.config)
    if args.sweep:
        if args.sweep not in p:
            parser.error("The sweep parameter must be an existing scalar input")
        if args.start is None or args.stop is None or args.points < 2:
            parser.error("A sweep needs --start, --stop and at least two points")
        if args.sweep in {"N", "N_y", "n_rep_P"}:
            parser.error("Use separate integer-valued configurations for this parameter")
    summary, terms = calculate(p)
    rows = []
    if args.sweep:
        for index in range(args.points):
            value = args.start + (args.stop - args.start) * index / (args.points - 1)
            changed = dict(p, **{args.sweep: value})
            if args.sweep in {"DoD_max", "DOD_max"}:
                changed.update(DoD_max=value, DOD_max=value)
            result, _ = calculate(changed)
            rows.append({"parameter": args.sweep, "parameter_value": value, **result})
    # No output directory is created until all requested calculations succeed.
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "parameters.json").write_text(json.dumps(p, indent=2) + "\n", encoding="utf-8")
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    write_csv(args.output / "summary.csv", [summary])
    if args.daily:
        _, _, costs, discounted_output, output = terms
        write_csv(args.output / "daily_output.csv", [
            {"day": i + 1, "delivered_energy_kWh": value,
             "discounted_delivered_energy_kWh": discounted_output[i],
             "discounted_charging_loss_cost_EUR": costs[i]}
            for i, value in enumerate(output)
        ])
    if rows:
        write_csv(args.output / "sensitivity.csv", rows)
    print(json.dumps(summary, indent=2))
    print(f"Saved to {args.output.resolve()}")


if __name__ == "__main__":
    main()
