#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import os
import json
import yaml
import hashlib
import pathlib
from typing import Optional, Annotated
import pandas as pd
import polars as pl
import numpy as np
import pymc as pm
import arviz as az
import pytensor.tensor as pt
import matplotlib.pyplot as plt
import seaborn as sns
from pydantic import BaseModel, model_validator, model_serializer, BeforeValidator

from myna.application.additivefoam import AdditiveFOAM


# Define data models and validation:
# - Experimental data model is the primary mode, with simulation data derived as a
#   subclass. This is intended to maintain that simulations are representations of the
#   experiments, so a subset of the simulation data model should directly correspond
#   to the experimental data
# - Before-validation gives some flexibility to the user, e.g., will not fail if user enters
#   a single value instead of a single-valued list
# - After-validation enforces expected data structure for the rest of the application


def _ensure_float_list(value):
    """BeforeValidator function to ensure that the value is a list[float]"""
    if isinstance(value, (int, float)):
        return [float(value)]
    return value


def _ensure_str_list(value):
    """BeforeValidator function to ensure that the value is a list[str]"""
    if isinstance(value, (str)):
        return [str(value)]
    return value


FlexibleFloatList = Annotated[list[float], BeforeValidator(_ensure_float_list)]
FlexibleStringList = Annotated[list[float], BeforeValidator(_ensure_str_list)]


class ProcessParameters(BaseModel):
    """Defines the process parameters that must be present for each experiment"""

    power: float  # heat source power, in W
    scan_speed: float  # heat source scan speed, in m/s
    spot_size: float  # diameter of the heat source, in mm


class SimulationParameters(BaseModel):
    """Defines the simulation parameters that define each simulation"""

    n: FlexibleFloatList  # description of heat source distribution, unitless


class SingleTrackData(BaseModel):
    """Defines the data required for a single track experiment"""

    process_parameters: ProcessParameters
    depths: FlexibleFloatList  # in millimeters
    comments: Optional[FlexibleStringList] = None

    # Serialize floats to 6 digits (0.001 micron precision for millimeters values)
    # to ensure for stable hashing
    @model_serializer(mode="wrap")
    def round_floats_serializer(self, handler):
        """Recursively rounds floats to 6 decimal places for stable hashing/JSON."""
        data = handler(self)
        return self._recursive_round(data)

    def _recursive_round(self, obj):
        if isinstance(obj, float):
            return round(obj, 6)
        if isinstance(obj, dict):
            return {k: self._recursive_round(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._recursive_round(x) for x in obj]
        return obj


class SimulatedSingleTrackData(SingleTrackData):
    """Defines the data required for a single track simulation"""

    simulation_parameters: SimulationParameters
    fingerprint: Optional[str] = None

    @model_validator(mode="after")
    def validate_lengths_match(self):
        if len(self.depths) != len(self.simulation_parameters.n):
            raise ValueError(
                "depths and simulation_parameters.n must have the same length"
            )
        return self


class ExperimentData(BaseModel):
    """Defines the format of the experimental data file"""

    data: list[SingleTrackData]
    comments: Optional[FlexibleStringList] = None

    def to_polars_df(self) -> pl.DataFrame:
        """Converts the data model to a polars DataFrame"""
        dicts = [
            {**d.process_parameters.model_dump(), "depths": d.depths} for d in self.data
        ]
        return pl.from_dicts(dicts)


class SimulationData(ExperimentData):
    """Defines the format of the simulation data file"""

    data: list[SimulatedSingleTrackData]

    def to_polars_df(self) -> pl.DataFrame:
        """Converts the data model to a polars DataFrame"""
        dicts = [
            {
                **d.process_parameters.model_dump(),
                **d.simulation_parameters.model_dump(),
                "depths": d.depths,
                "fingerprint": d.fingerprint,
            }
            for d in self.data
        ]
        # TODO: Consider using the `explode(["depths", "n"])` feature to get a single
        #       row per datum. This may simplify the logic for fingerprinting and
        #       simulation queueing
        return pl.from_dicts(dicts)


def create_data_fingerprint(data: ExperimentData | SimulationData) -> str:
    """Create a hash from the experiment or simulation data for quick comparison of
    sameness to previous datasets.

    While this approach ensures that the fields are in a consistent order, this will
    return a different hash if the listed values, e.g., `depths`, change order."""
    # Format payload, ensuring consistent ordering and removing whitespace
    payload = data.model_dump(mode="json", exclude={"fingerprint"}, exclude_none=True)
    canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode()).hexdigest()


def load_dict_file(filepath: str | pathlib.Path) -> dict:
    """Loads a dictionary from a JSON or YAML file"""
    # Check if the file exists
    if not os.path.exists(filepath):
        print(f"Info: File not found at '{filepath}'. Proceeding with empty data.")
        return {}
    with open(filepath, "r") as f:
        suffix = pathlib.Path(filepath).suffix
        if suffix in [".yml", ".yaml"]:
            return yaml.safe_load(f)
        elif suffix in [".json"]:
            return json.load(f)
        return {}


# def parse_experiments(raw_experiments: list) -> pd.DataFrame:
#     if not raw_experiments:
#         return pd.DataFrame(
#             columns=[
#                 "parameters",
#                 "depths_list",
#                 "normalized_depths_list",
#                 "fingerprint",
#             ]
#         )
#     records = []
#     for exp in raw_experiments:
#         params = exp["parameters"]
#         spot_size = params.get("Spot_Size_microns")
#         if spot_size is None or spot_size <= 0:
#             print(
#                 f"Warning: Invalid or missing 'Spot_Size_microns' in parameters {params}. Skipping this experiment."
#             )
#             continue

#         depths = exp["Measured_Depth_microns"]
#         normalized_depths = [d / spot_size for d in depths]

#         records.append(
#             {
#                 "parameters": params,
#                 "depths_list": depths,
#                 "normalized_depths_list": normalized_depths,
#                 "fingerprint": create_data_fingerprint(depths),
#             }
#         )
#     return pd.DataFrame(records)


# def parse_simulations(raw_simulations: list) -> pd.DataFrame:
#     if not raw_simulations:
#         return pd.DataFrame()
#     records = []
#     for sim_run in raw_simulations:
#         params, n_values, depths = (
#             sim_run["parameters"],
#             sim_run["n"],
#             sim_run["Simulated_Depth_microns"],
#         )
#         spot_size = params.get("Spot_Size_microns")
#         if spot_size is None or spot_size <= 0:
#             print(
#                 f"Warning: Invalid or missing 'Spot_Size_microns' in parameters {params}. Skipping this simulation set."
#             )
#             continue

#         for n, depth in zip(n_values, depths):
#             records.append(
#                 {
#                     **params,
#                     "n": n,
#                     "Simulated_Depth_microns": depth,
#                     "Normalized_Simulated_Depth": depth / spot_size,
#                 }
#             )
#     return pd.DataFrame(records)


def save_state_file(state_data: list, filepath: str):
    print(f"\nSaving updated state to '{filepath}'...")
    try:
        with open(filepath, "w") as f:
            yaml.dump(
                state_data,
                f,
                default_flow_style=False,
                sort_keys=False,
                indent=2,
            )
        print("Save complete.")
    except Exception as e:
        print(f"Error saving state file '{filepath}': {e}")


def save_simulation_queue(queue_df: pd.DataFrame, filepath: str):
    print(f"Saving pending simulation queue to '{filepath}'...")
    try:
        queue_df.to_csv(filepath, index=False)
        print("Queue saved successfully.")
    except Exception as e:
        print(f"Error saving simulation queue file '{filepath}': {e}")


# ==============================================================================
# SECTION 2: CORE CALIBRATION LOGIC
# ==============================================================================
def linear_interp_pt(n_val, n_data_pt, column_data_pt):
    n_data_pt, column_data_pt, n_val = (
        pt.cast(n_data_pt, "float64"),
        pt.cast(column_data_pt, "float64"),
        pt.cast(n_val, "float64"),
    )
    idx, data_len = pt.searchsorted(n_data_pt, n_val), pt.shape(n_data_pt)[0]
    idx = pt.clip(idx, 1, data_len - 1)
    idx_lower, idx_upper = idx - 1, idx
    n_lower, n_upper = n_data_pt[idx_lower], n_data_pt[idx_upper]
    val_lower, val_upper = column_data_pt[idx_lower], column_data_pt[idx_upper]
    return val_lower + (val_upper - val_lower) * (n_val - n_lower) / (n_upper - n_lower)


def perform_bayesian_calibration(
    n_coords: np.ndarray, model_values: np.ndarray, observed_values: list[float]
) -> az.InferenceData:
    sigma_est = (
        np.std(observed_values)
        if len(observed_values) > 1
        else 0.15 * observed_values[0]
    )
    sigma_est = max(
        sigma_est, 1e-4
    )  # Adjusted minimum sigma for smaller normalized values
    with pm.Model() as model:
        n = pm.Uniform("n", lower=n_coords.min(), upper=n_coords.max())
        n_data_pt, model_values_pt = pt.constant(n_coords), pt.constant(model_values)
        predicted_value = pm.Deterministic(
            "predicted_value", linear_interp_pt(n, n_data_pt, model_values_pt)
        )
        pm.Normal(
            "likelihood",
            mu=predicted_value,
            sigma=sigma_est,
            observed=observed_values,
        )
        print(
            f"  Sampling posterior with {len(observed_values)} observations (σ_est={sigma_est:.3f})..."
        )
        trace = pm.sample(
            draws=2000,
            tune=1000,
            cores=8,
            progressbar=True,
            target_accept=0.9,
            random_seed=42,
        )
    return trace


def extract_calibrated_n(trace: az.InferenceData, n_min: float, n_max: float) -> float:
    n_samples = trace.posterior["n"].values.flatten()
    posterior_mean_n = np.mean(n_samples)
    lower_bound_region = n_min + (n_max - n_min) * 0.01
    clipping_percentage = np.sum(n_samples <= lower_bound_region) / len(n_samples) * 100
    if clipping_percentage > 5.0:
        print(
            f"  Warning: Posterior is clipped at lower bound ({clipping_percentage:.1f}%). Using n_min."
        )
        return n_min
    return posterior_mean_n


# ==============================================================================
# SECTION 3: PLOTTING AND ANALYSIS FUNCTIONS
# ==============================================================================
def plot_calibration_overview(results_df, simulations_df):
    if results_df.empty:
        return
    num_plots = len(results_df)
    fig, axes = plt.subplots(
        1, num_plots, figsize=(6 * num_plots, 5), sharey=True, squeeze=False
    )
    axes = axes.flatten()
    for i, (_, row) in enumerate(results_df.iterrows()):
        params_dict = row["parameters"]
        ax = axes[i]
        query_string = " & ".join([f"`{k}`=={v}" for k, v in params_dict.items()])
        sim_curve = simulations_df.query(query_string).sort_values("n")

        # Plot normalized simulation curve
        ax.plot(
            sim_curve["n"],
            sim_curve["Normalized_Simulated_Depth"],
            "k-",
            label="Simulation Curve",
            zorder=1,
        )

        # Plot calibrated point against mean normalized experimental depth
        ax.errorbar(
            x=row["calibrated_n"],
            y=row["mean_normalized_depth"],
            xerr=row["calibrated_n_std"],
            fmt="o",
            color="red",
            capsize=5,
            markersize=8,
            label="Calibrated n (Mean & Std Dev)",
            zorder=3,
        )

        # Plot individual normalized experimental data points
        ax.scatter(
            np.full(len(row["normalized_depths_list"]), row["calibrated_n"]),
            row["normalized_depths_list"],
            edgecolor="blue",
            facecolor="none",
            s=50,
            label="Experimental Data",
            zorder=2,
        )

        title = ", ".join([f"{k.split('_')[0]}={v}" for k, v in params_dict.items()])
        ax.set_title(title), ax.set_xlabel("Shape Factor (n)"), ax.grid(
            True, linestyle="--", alpha=0.6
        )

    axes[0].set_ylabel("Normalized Melt Pool Depth (Depth / Spot Size)"), axes[
        0
    ].legend()
    fig.suptitle(
        "Calibration Overview of Newly Processed Experiments",
        fontsize=16,
        y=1.02,
    ), plt.tight_layout(), plt.show()


def plot_posterior_distributions(traces_dict):
    if not traces_dict:
        return
    plt.figure(figsize=(10, 6))
    colors = plt.cm.viridis(np.linspace(0, 1, len(traces_dict)))
    for i, (param_key, trace) in enumerate(traces_dict.items()):
        params_dict = dict(eval(param_key))
        label = ", ".join([f"{k.split('_')[0]}={v}" for k, v in params_dict.items()])
        sns.histplot(
            trace.posterior["n"].values.flatten(),
            label=label,
            color=colors[i],
            kde=True,
            alpha=0.5,
            stat="probability",
        )
    plt.title("Posterior Distributions for Newly Calibrated 'n'"), plt.xlabel(
        "Calibrated n Value"
    ), plt.ylabel("Density")
    plt.legend(
        title="Process Parameters", bbox_to_anchor=(1.05, 1), loc="upper left"
    ), plt.grid(True, linestyle="--", alpha=0.6), plt.tight_layout(), plt.show()


def fit_and_plot_heteroskedastic_model(calibrated_results_df):
    """
    Performs a robust heteroskedastic Bayesian regression to model both the mean
    and the standard deviation of n as a function of NORMALIZED depth.
    """
    if calibrated_results_df.empty or len(calibrated_results_df) < 2:
        print("Info: Not enough newly calibrated points to fit a final relationship.")
        return

    normalized_depths_obs = calibrated_results_df["mean_normalized_depth"].values
    n_obs = calibrated_results_df["calibrated_n"].values
    n_stds_obs = calibrated_results_df["calibrated_n_std"].values

    with pm.Model() as hetero_model:
        # --- Model Priors ---
        A = pm.Normal("A", mu=1.0, sigma=2.0)
        B = pm.Normal("B", mu=0.0, sigma=5.0)
        C = pm.Normal("C", mu=0.0, sigma=1.0)
        D = pm.Normal("D", mu=0.0, sigma=2.0)
        nu = pm.Exponential("nu", 1 / 29.0) + 1

        # --- Model Definition (using normalized depth) ---
        mu_model = pm.Deterministic("mu", A * pt.log2(normalized_depths_obs) + B)
        log_sigma_model = pm.Deterministic(
            "log_sigma", C * pt.log2(normalized_depths_obs) + D
        )
        sigma_model = pm.Deterministic("sigma", pt.exp(log_sigma_model))

        pm.StudentT("n_fit", nu=nu, mu=mu_model, sigma=sigma_model, observed=n_obs)

        print("\n--- Performing Robust Heteroskedastic Fit ---")
        hetero_trace = pm.sample(
            2000, tune=1500, cores=4, random_seed=42, target_accept=0.95
        )

    print("\n--- Heteroskedastic Fit Summary ---")
    print(az.summary(hetero_trace, var_names=["A", "B", "C", "D", "nu"]))

    # --- Plotting the Results ---
    fig, ax = plt.subplots(figsize=(10, 6))

    post = hetero_trace.posterior
    A_m, B_m = post["A"].mean().item(), post["B"].mean().item()
    C_m, D_m = post["C"].mean().item(), post["D"].mean().item()

    # Plot the observed data points with their Stage 1 uncertainty
    ax.errorbar(
        normalized_depths_obs,
        n_obs,
        yerr=n_stds_obs,
        fmt="o",
        color="C0",
        ecolor="C0",
        capsize=3,
        label="Calibrated n (from Stage 1)",
    )

    # Calculate and plot the model's prediction for the mean
    x_range = np.linspace(
        normalized_depths_obs.min() * 0.9,
        normalized_depths_obs.max() * 1.1,
        100,
    )
    mean_pred = A_m * np.log2(x_range) + B_m
    ax.plot(x_range, mean_pred, color="C1", lw=2, label=f"Mean Model: n(d_norm)")

    # Calculate and plot the model's prediction for the uncertainty (±2 sigma)
    sigma_pred = np.exp(C_m * np.log2(x_range) + D_m)
    ax.fill_between(
        x_range,
        mean_pred - 2.0 * 0.1 * mean_pred,  # sigma_pred,
        mean_pred + 2.0 * 0.1 * mean_pred,  # sigma_pred,
        color="C1",
        alpha=0.3,
        label=f"Uncertainty Model: ±2σ(d_norm)",
    )

    ax.set_title("Heteroskedastic Fit of 'n' vs. Mean Normalized Experimental Depth")
    ax.set_xlabel(
        "Mean Normalized Experimental Depth (Depth / Spot Size)"
    ), ax.set_ylabel("Calibrated Shape Factor (n)")
    ax.legend(), ax.grid(True, linestyle="--", alpha=0.6), plt.tight_layout()
    ax.set_xscale("log", base=2)
    plt.show()

    print("\n--- Final Predictive Equations (Using Normalized Depth d_norm) ---")
    print(
        f"To predict the mean n:       n_mean(d_norm) = {A_m:.4f} * log2(d_norm) + {B_m:.4f}"
    )
    print(
        f"To predict the uncertainty (σ): σ_n(d_norm)    = exp({C_m:.4f} * log2(d_norm) + {D_m:.4f})"
    )


########################################################################################
#                                                                                      #
################### Myna Class for AdditiveFOAM Calibration ############################
#                                                                                      #
########################################################################################


class AdditiveFOAMCalibration(AdditiveFOAM):
    """Application to generated calibrated heat source parameters for AdditiveFOAM"""

    def execute(self):
        # Set paths
        EXPERIMENTS_PATH = "experiments.yml"
        SIMULATIONS_PATH = "simulations.yml"
        STATE_PATH = "calibration_state.yml"
        SIMULATION_QUEUE_PATH = "pending_simulations.csv"

        # Load and validate data models from dictionaries
        experiments = ExperimentData(**load_dict_file(EXPERIMENTS_PATH))
        simulations = SimulationData(**load_dict_file(SIMULATIONS_PATH))

        # TODO: delete below old code (3 lines)
        raw_experiments = load_dict_file(EXPERIMENTS_PATH)
        raw_simulations = load_dict_file(SIMULATIONS_PATH)
        current_state_data = load_dict_file(STATE_PATH)

        # Load data to dataframe
        df_exp = experiments.to_polars_df()
        df_sim = simulations.to_polars_df()

        # TODO: repalce `exp_df` and `sim_df` with newer `df_exp` and `df_sim` implementations
        exp_df, sim_df, state_df = (
            parse_experiments(raw_experiments),
            parse_simulations(raw_simulations),
            pd.DataFrame(current_state_data),
        )
        if exp_df.empty:
            print("\nNo experimental data found. Exiting."), exit()

        to_process_list, fresh_states, state_lookup = [], [], {}
        if not state_df.empty:
            for i, row in state_df.iterrows():
                state_lookup[str(sorted(row["parameters"].items()))] = row.to_dict()
        for _, exp_row in exp_df.iterrows():
            param_key = str(sorted(exp_row["parameters"].items()))
            if (
                param_key in state_lookup
                and state_lookup[param_key].get("fingerprint") == exp_row["fingerprint"]
            ):
                fresh_states.append(state_lookup[param_key])
            else:
                to_process_list.append(exp_row)
        to_process_df = pd.DataFrame(to_process_list)
        print("\n--- Adaptive Run Summary ---"), print(
            f"Found {len(exp_df)} total experimental parameter sets."
        )
        print(f"Found {len(fresh_states)} up-to-date calibrations."), print(
            f"Found {len(to_process_df)} new or stale experiments to process."
        )
        newly_calibrated_states, needs_simulation_list, posterior_traces = (
            [],
            [],
            {},
        )
        newly_calibrated_results_for_plotting = []
        if not to_process_df.empty and sim_df.empty:
            print(
                "\nWarning: Experiments need processing, but simulation data is empty. Flagging all as 'needs simulation'."
            )
            needs_simulation_list = to_process_df["parameters"].tolist()
        elif not to_process_df.empty:
            for _, job_row in to_process_df.iterrows():
                params = job_row["parameters"]
                print(f"\n--- Processing parameters: {params} ---")
                query_string = " & ".join([f"`{k}`=={v}" for k, v in params.items()])
                model_subset = sim_df.query(query_string)
                if model_subset.empty:
                    print(
                        "  FLAGGED: No matching simulation data found."
                    ), needs_simulation_list.append(params)
                    continue
                print("  Found matching simulation data. Proceeding with calibration.")

                model_subset_sorted = model_subset.sort_values(by="n")
                n_coords = model_subset_sorted["n"].values
                model_normalized_depths = model_subset_sorted[
                    "Normalized_Simulated_Depth"
                ].values

                trace = perform_bayesian_calibration(
                    n_coords,
                    model_normalized_depths,
                    job_row["normalized_depths_list"],
                )

                calibrated_n_mean = extract_calibrated_n(
                    trace, n_min=n_coords.min(), n_max=n_coords.max()
                )
                calibrated_n_std = trace.posterior["n"].values.std()
                new_state = {
                    "parameters": params,
                    "calibrated_n": float(calibrated_n_mean),
                    "calibrated_n_std": float(calibrated_n_std),
                    "fingerprint": job_row["fingerprint"],
                }
                newly_calibrated_states.append(new_state)
                posterior_traces[str(sorted(params.items()))] = trace

                newly_calibrated_results_for_plotting.append(
                    {
                        **new_state,
                        "mean_normalized_depth": np.mean(
                            job_row["normalized_depths_list"]
                        ),
                        "normalized_depths_list": job_row["normalized_depths_list"],
                    }
                )

                print(
                    f"  -> Calibrated n: {calibrated_n_mean:.3f} ± {calibrated_n_std:.3f}"
                )
        final_state = fresh_states + newly_calibrated_states
        save_state_file(final_state, STATE_PATH)
        final_state_df = pd.DataFrame(final_state)
        print("\n\n" + "=" * 30), print(" FINAL CALIBRATION STATE "), print("=" * 30)
        if not final_state_df.empty:
            print(
                final_state_df[
                    ["parameters", "calibrated_n", "calibrated_n_std"]
                ].to_string(index=False, float_format="%.4f")
            )
        else:
            print("No calibrated results exist in the state file.")
        print("\n\n" + "=" * 35), print(
            " ACTION REQUIRED: PENDING SIMULATIONS "
        ), print("=" * 35)
        needs_simulation_df = pd.DataFrame(needs_simulation_list)
        if not needs_simulation_df.empty:
            print(
                f"The following parameter sets require a simulation run (saved to '{SIMULATION_QUEUE_PATH}'):"
            ), print(needs_simulation_df.to_string(index=False))
            save_simulation_queue(needs_simulation_df, SIMULATION_QUEUE_PATH)
        else:
            print("No new simulations are required at this time.")
        if newly_calibrated_results_for_plotting:
            print("\nGenerating plots for newly calibrated data...")
            plot_df = pd.DataFrame(newly_calibrated_results_for_plotting)
            plot_calibration_overview(plot_df, sim_df)
            plot_posterior_distributions(posterior_traces)
            fit_and_plot_heteroskedastic_model(plot_df)
        print("\nDone.")
