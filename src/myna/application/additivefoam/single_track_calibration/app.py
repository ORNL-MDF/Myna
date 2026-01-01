#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import os
import yaml
import shutil
import pathlib
import logging
from typing import Optional
from dataclasses import asdict
import polars as pl
import numpy as np
import pymc as pm
import arviz as az
import pytensor.tensor as pt
from myna.application.additivefoam import AdditiveFOAM
from myna.application.additivefoam.single_track_calibration.models import (
    ExperimentData,
    SimulationData,
    ProcessParameters,
    CalibrationConfig,
    create_row_fingerprint,
)
from myna.core.utils.filesystem import load_json_yaml_file

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Define calibration logic
def linear_interp_pt(n_val, n_data_pt, column_data_pt):
    """Linear interpolation using PyTensor tensors"""
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
    n_coords: list[float | int],
    model_values: list[float | int],
    observed_values: list[list[float | int]],
) -> az.InferenceData:
    """Calculates the posterior distribution from Bayesian calibration of n to observations

    Assumptions:
    - Uniform prior
    - 1 Gaussian standard deviation is used as noise if multiple observations are given,
      otherwise 15% of the measured value is used as noise
    """
    # Convert to numpy arrays to handle both lists and Polars Series
    observed_arrays = [np.asarray(x) for x in observed_values]
    sigmas = np.array(
        [
            max(np.std(arr) if len(arr) > 1 else 0.15 * arr[0], 1e-4)
            for arr in observed_arrays
        ]
    )

    with pm.Model() as _:
        n = pm.Uniform("n", lower=np.min(n_coords), upper=np.max(n_coords))
        n_data_pt, model_values_pt = pt.constant(n_coords), pt.constant(model_values)
        predicted_values = pm.Deterministic(
            "predicted_value", linear_interp_pt(n, n_data_pt, model_values_pt)
        )
        pm.Normal(
            "likelihood",
            mu=predicted_values,
            sigma=sigmas,
            observed=observed_values,
        )
        logger.info(
            f"Sampling posterior with {len(observed_values)} observations "
            f"(σ_est={sigmas})"
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
    """Extract calibrated n value from posterior samples"""
    n_samples = trace.posterior["n"].values.flatten()  # type: ignore[attr-defined] arviz uses dynamic attributes
    posterior_mean_n = np.mean(n_samples)
    lower_bound_region = n_min + (n_max - n_min) * 0.01
    clipping_percentage = np.sum(n_samples <= lower_bound_region) / len(n_samples) * 100

    if clipping_percentage > 5.0:
        logger.warning(
            f"Posterior is clipped at lower bound ({clipping_percentage:.1f}%). "
            f"Using n_min={n_min:.3f}"
        )
        return n_min

    return posterior_mean_n


# ==============================================================================
# SECTION 3: MAIN CALIBRATION APPLICATION
# ==============================================================================


class AdditiveFOAMCalibration(AdditiveFOAM):
    """Application to generate calibrated heat source parameters for AdditiveFOAM

    This class orchestrates:
    1. Loading experimental and simulation data
    2. Identifying missing simulations
    3. Running required simulations
    4. Performing Bayesian calibration
    5. Saving results
    """

    def __init__(
        self,
        name: str = "single_track_calibration",
        config: Optional[CalibrationConfig] = None,
    ):
        super().__init__(name)
        self.config = config or CalibrationConfig()
        self.config_file = "config.yaml"
        self.logger = logging.getLogger(f"{__name__}.{name}")

    def parse_configure_arguments(self):
        """Check for arguments relevant to the configure step and update app settings"""
        self.parser.add_argument(
            "--experiments",
            default="experiments.yaml",
            type=str,
            help="Path to the experiemnts file",
        )
        self.parser.add_argument(
            "--simulations",
            default=None,
            type=str,
            help=(
                "(optional) Path to an existing simulations file."
                "A new file will be created if not given."
            ),
        )
        self.parser.add_argument(
            "--calibrations",
            default=None,
            type=str,
            help=(
                "(optional) Path to an existing calibrations file."
                "A new file will be created if not given."
            ),
        )
        self.parser.add_argument(
            "--nvalues",
            default=[1.0, 5.0, 9.0],
            type=float,
            nargs="+",
            help="",
        )
        self.parse_known_args()

    def configure(self):
        """Configure all cases"""
        # TODO: update to inherit/determine case list from app type
        cases = ["./test_dir"]
        cases = [pathlib.Path(case) for case in cases]
        self.parse_configure_arguments()
        print(f"{self.args=}")
        for case in cases:
            os.makedirs(case, exist_ok=True)
            self.configure_case(case)

    def configure_case(self, case_dir: str | pathlib.Path):
        """Configures the case directory associated with the step"""
        # Use pathlib inside function
        if not isinstance(case_dir, pathlib.Path):
            case_dir = pathlib.Path(case_dir)

        # Get experiments file
        experiments_path = self.args.experiments

        # Get/create simulations file
        simulations_path = f"{case_dir}/simulations.yaml"
        if self.args.simulations is not None:
            shutil.copy(self.args.simulations, simulations_path)

        # Get/create calibrations file
        calibrations_path = f"{case_dir}/calibrations.yaml"
        if self.args.calibrations is not None:
            shutil.copy(self.args.calibrations, calibrations_path)

        # Set simulation output path
        simulation_output_dir = f"{case_dir}/sim_output"
        n_values = self.args.nvalues

        # Create configuration object to ensure it is valid
        config = CalibrationConfig(
            experiments_path=experiments_path,
            simulations_path=simulations_path,
            calibrations_path=calibrations_path,
            simulation_output_dir=simulation_output_dir,
            n_values=n_values,
        )

        # Write configuration class to file
        config_path = case_dir / self.config_file
        with open(config_path, mode="w", encoding="utf-8") as f:
            yaml.dump(asdict(config), f, sort_keys=False, default_flow_style=False)

        # Archive experimental data with the case directory
        shutil.copy(experiments_path, case_dir / pathlib.Path(experiments_path).name)

    def execute(self):
        """Execute all cases"""
        # TODO: update to inherit/determine case list from app type
        cases = ["./test_dir"]
        for case in cases:
            config_path = pathlib.Path(case) / self.config_file
            config = CalibrationConfig(
                **load_json_yaml_file(config_path, enforce_type=dict)
            )
            self.execute_case(config)

    def execute_case(self, config: CalibrationConfig):
        """Main execution flow - orchestrates the calibration workflow"""
        self.config = config
        self.logger.info("=" * 80)
        self.logger.info("Starting AdditiveFOAM Calibration Workflow")
        self.logger.info("=" * 80)

        try:
            # 1. Load data
            self.logger.info("Step 1: Loading data files")
            experiments, simulations, calibrations = self._load_all_data()

            # 2. Build simulation matrix and identify missing/invalid simulations
            self.logger.info("Step 2: Building simulation queue")
            sim_queue = self._build_simulation_queue(experiments, simulations)

            # 3. Run missing simulations
            if len(sim_queue) > 0:
                self.logger.info(f"Step 3: Running {len(sim_queue)} simulations")
                simulations = self._run_simulations(sim_queue, simulations)
                self._save_simulations(simulations)
            else:
                self.logger.info("Step 3: No simulations needed - all up to date")

            # 4. Perform Bayesian calibration
            self.logger.info("Step 4: Performing Bayesian calibration")
            calibrations = self._perform_calibration(experiments, simulations)
            self._save_calibrations(calibrations)

            self.logger.info("=" * 80)
            self.logger.info("Calibration workflow completed successfully!")
            self.logger.info(f"Results saved to: {self.config.calibrations_path}")
            self.logger.info("=" * 80)

        except Exception as e:
            self.logger.error(f"Calibration workflow failed: {str(e)}", exc_info=True)
            raise

    def _load_all_data(self) -> tuple[ExperimentData, SimulationData, list]:
        """Load and validate all input data files"""
        # Load experiments
        try:
            exp_dict = load_json_yaml_file(
                self.config.experiments_path, enforce_type=dict
            )
            experiments = ExperimentData(**exp_dict)
            self.logger.info(
                f"Loaded {len(experiments.data)} experimental records from "
                f"{self.config.experiments_path}"
            )
        except FileNotFoundError:
            self.logger.error(
                f"Experiment file not found: {self.config.experiments_path}"
            )
            raise
        except Exception as e:
            self.logger.error(f"Failed to load experiments: {str(e)}")
            raise

        # Load simulations
        try:
            sim_dict = load_json_yaml_file(
                self.config.simulations_path, enforce_type=dict
            )
            simulations = SimulationData(**sim_dict)
            self.logger.info(
                f"Loaded {len(simulations.data)} simulation records from "
                f"{self.config.simulations_path}"
            )
        except FileNotFoundError:
            self.logger.warning(
                f"Simulation file not found: {self.config.simulations_path}. "
                f"Starting with empty simulation set."
            )
            simulations = SimulationData(data=[])
        except Exception as e:
            self.logger.error(f"Failed to load simulations: {str(e)}")
            raise

        # Load calibrations
        try:
            calibrations = list(
                load_json_yaml_file(self.config.calibrations_path, enforce_type=list)
            )
            self.logger.info(
                f"Loaded existing calibrations from {self.config.calibrations_path}"
            )
        except FileNotFoundError:
            self.logger.info("No existing calibrations found. Will create new file.")
            calibrations = []

        return experiments, simulations, calibrations

    def _build_simulation_queue(
        self, experiments: ExperimentData, simulations: SimulationData
    ) -> pl.DataFrame:
        """Determine which simulations need to be run

        Returns a DataFrame with one row per simulation to run, containing:
        - Process parameters (power, scan_speed, spot_size)
        - Simulation parameter (n)
        - fingerprint for tracking
        """
        self.logger.debug("Preparing experiment and simulation DataFrames")
        df_exp = self._prepare_experiment_df(experiments)
        df_sim = self._prepare_simulation_df(simulations)

        self.logger.debug("Creating required simulation matrix")
        required_sims = self._create_required_simulation_matrix(df_exp)
        self.logger.info(f"Total required simulations: {len(required_sims)}")

        self.logger.debug("Identifying valid existing simulations")
        valid_sims = self._identify_valid_simulations(df_sim)
        self.logger.info(f"Valid existing simulations: {len(valid_sims)}")

        # Find missing simulations (anti-join)
        sim_queue = required_sims.join(
            valid_sims.select(["fingerprint", "n"]), on=["fingerprint", "n"], how="anti"
        )

        self.logger.info(f"Simulations to run: {len(sim_queue)}")

        if len(sim_queue) > 0:
            # Log details about what needs to be run
            queue_summary = sim_queue.group_by("fingerprint").agg(
                pl.col("n").count().alias("n_count")
            )
            for row in queue_summary.iter_rows(named=True):
                self.logger.debug(
                    f"  Fingerprint {row['fingerprint'][:8]}...: "
                    f"{row['n_count']} simulations"
                )

        return sim_queue

    def _prepare_experiment_df(self, experiments: ExperimentData) -> pl.DataFrame:
        """Convert experiments to DataFrame with fingerprints"""
        df = experiments.to_polars_df()

        # Add fingerprints based on process parameters
        param_cols = list(ProcessParameters.model_fields.keys())
        df = df.with_columns(
            pl.struct([pl.col(k) for k in param_cols])
            .map_elements(create_row_fingerprint, return_dtype=pl.String)
            .alias("fingerprint")
        )

        self.logger.debug(f"Prepared experiment DataFrame: {len(df)} rows")
        return df

    def _prepare_simulation_df(self, simulations: SimulationData) -> pl.DataFrame:
        """Convert simulations to DataFrame and validate fingerprints"""
        if len(simulations.data) == 0:
            self.logger.debug("No existing simulations - returning empty DataFrame")
            return pl.DataFrame(
                schema={
                    **{k: pl.Float64 for k in ProcessParameters.model_fields},
                    "n": pl.Float64,
                    "depths": pl.Float64,
                    "fingerprint": pl.String,
                    "current_fingerprint": pl.String,
                }
            )

        df = simulations.to_polars_df()

        # Check for fingerprint mismatches
        mismatches = df.filter(
            pl.col("fingerprint").is_not_null()
            & (pl.col("fingerprint") != pl.col("current_fingerprint"))
        )

        if len(mismatches) > 0:
            self.logger.warning(
                f"Found {len(mismatches)} simulations with outdated fingerprints "
                f"(process parameters changed). These will be re-run."
            )

        self.logger.debug(f"Prepared simulation DataFrame: {len(df)} rows")
        return df

    def _create_required_simulation_matrix(self, df_exp: pl.DataFrame) -> pl.DataFrame:
        """Create full matrix of all simulations that should exist"""
        # Get unique experiment fingerprints
        param_cols = list(ProcessParameters.model_fields.keys())
        unique_experiments = df_exp.select([*param_cols, "fingerprint"]).unique()

        self.logger.debug(f"Unique experiments: {len(unique_experiments)}")

        # Cross join with all n values
        n_df = pl.DataFrame({"n": self.config.n_values})
        required_sims = unique_experiments.join(n_df, how="cross")

        self.logger.debug(
            f"Required simulation matrix: {len(unique_experiments)} experiments x "
            f"{len(self.config.n_values) if isinstance(self.config.n_values, list) else None} "
            "n-values = {len(required_sims)} simulations"
        )

        return required_sims

    def _identify_valid_simulations(self, df_sim: pl.DataFrame) -> pl.DataFrame:
        """Filter simulations to only those that are valid

        Valid simulations must:
        1. Have matching stored and current fingerprints (process params unchanged)
        2. Have non-null depth results
        """
        if len(df_sim) == 0:
            return df_sim

        valid = df_sim.filter(
            (pl.col("fingerprint") == pl.col("current_fingerprint"))
            & (pl.col("depths").is_not_null())
        )

        invalid_count = len(df_sim) - len(valid)
        if invalid_count > 0:
            self.logger.debug(f"Filtered out {invalid_count} invalid simulations")

        return valid

    def _run_simulations(
        self, sim_queue: pl.DataFrame, existing_sims: SimulationData
    ) -> SimulationData:
        """Execute simulations for all entries in the queue"""
        os.makedirs(self.config.simulation_output_dir, exist_ok=True)
        self.logger.info(f"Output directory: {self.config.simulation_output_dir}")

        def _run_single_simulation(row) -> float:
            """Run a single simulation

            TODO: Replace with actual AdditiveFOAM simulation call
            """
            # Extract parameters for logging
            power = row["power"]
            speed = row["scan_speed"]
            spot = row["spot_size"]
            n = row["n"]

            self.logger.debug(
                f"Running simulation: P={power}W, v={speed}m/s, " f"d={spot}mm, n={n}"
            )

            # Placeholder - replace with actual simulation
            result = np.random.rand() * 0.5 + 0.1  # Random depth between 0.1-0.6 mm

            self.logger.debug(f"  Result: depth={result:.4f}mm")
            return result

        # Run simulations with progress tracking
        self.logger.info("Executing simulations...")
        results = sim_queue.with_columns(
            pl.struct(pl.all())
            .map_elements(_run_single_simulation, return_dtype=pl.Float64)
            .alias("depths")
        )

        # Mark these simulations as validated
        results = results.with_columns(
            pl.col("fingerprint").alias("current_fingerprint")
        )

        self.logger.info(f"Completed {len(results)} simulations")

        # Merge with existing valid simulations
        df_sim_existing = existing_sims.to_polars_df()
        df_sim_valid = self._identify_valid_simulations(df_sim_existing)

        # Combine valid existing + new results
        combined = pl.concat([df_sim_valid, results], how="diagonal_relaxed")

        self.logger.debug(
            f"Combined simulations: {len(df_sim_valid)} existing + "
            f"{len(results)} new = {len(combined)} total"
        )

        # Update the simulation data model
        updated_sims = SimulationData(data=[])
        updated_sims.update_from_df(combined)

        self.logger.info(
            f"Updated simulation data model with {len(updated_sims.data)} records"
        )

        return updated_sims

    def _perform_calibration(
        self, experiments: ExperimentData, simulations: SimulationData
    ) -> list[dict]:
        """Perform Bayesian calibration for each experiment"""
        df_exp = self._prepare_experiment_df(experiments)
        df_sim = self._prepare_simulation_df(simulations)
        df_sim_valid = self._identify_valid_simulations(df_sim)

        calibration_results = []
        unique_fingerprints = df_exp.select("fingerprint").unique().to_series()

        self.logger.info(f"Calibrating {len(unique_fingerprints)} experiments")

        for i, fingerprint in enumerate(unique_fingerprints, 1):
            self.logger.info(
                f"Calibration {i}/{len(unique_fingerprints)}: {fingerprint[:16]}..."
            )

            try:
                # Get experimental observations
                exp_data = df_exp.filter(pl.col("fingerprint") == fingerprint)
                observed_depths = exp_data.select("depths").to_series()[0]
                if not isinstance(observed_depths, list):
                    observed_depths = (
                        observed_depths.to_list()
                        if hasattr(observed_depths, "to_list")
                        else [observed_depths]
                    )

                # Get simulation results for all n values
                sim_data = df_sim_valid.filter(
                    pl.col("current_fingerprint") == fingerprint
                ).sort("n")

                if len(sim_data) < 2:
                    self.logger.warning(
                        f"  Skipping: insufficient simulation data "
                        f"({len(sim_data)} points, need ≥2)"
                    )
                    continue

                n_coords = sim_data.select("n").to_series().to_list()
                model_depths = sim_data.select("depths").to_series().to_list()

                self.logger.debug(
                    f"  n range: [{min(n_coords):.1f}, {max(n_coords):.1f}], "
                    f"depth range: [{min(model_depths):.4f}, {max(model_depths):.4f}]mm"
                )

                # Perform calibration
                trace = perform_bayesian_calibration(
                    n_coords=n_coords,
                    model_values=model_depths,
                    observed_values=[[d] for d in observed_depths],
                )

                calibrated_n = extract_calibrated_n(
                    trace, n_min=min(n_coords), n_max=max(n_coords)
                )

                # Calculate uncertainty metrics
                n_samples = trace.posterior["n"].values.flatten()  # type: ignore[attr-defined] arviz uses dynamic attributes
                n_std = np.std(n_samples)
                n_ci_lower = np.percentile(n_samples, 2.5)
                n_ci_upper = np.percentile(n_samples, 97.5)

                self.logger.info(
                    f"  ✓ Calibrated n = {calibrated_n:.3f} ± {n_std:.3f} "
                    f"(95% CI: [{n_ci_lower:.3f}, {n_ci_upper:.3f}])"
                )

                # Store results
                process_params = exp_data.select(
                    list(ProcessParameters.model_fields.keys())
                ).row(0, named=True)

                calibration_results.append(
                    {
                        "fingerprint": fingerprint,
                        "process_parameters": process_params,
                        "calibrated_n": float(calibrated_n),
                        "n_std": float(n_std),
                        "n_ci_lower": float(n_ci_lower),
                        "n_ci_upper": float(n_ci_upper),
                        "n_samples": n_samples.tolist(),
                        "observed_depths": observed_depths,
                    }
                )

            except Exception as e:
                self.logger.error(
                    f"  ✗ Calibration failed for {fingerprint[:16]}: {str(e)}",
                    exc_info=True,
                )
                continue

        self.logger.info(
            f"Successfully calibrated {len(calibration_results)} experiments"
        )
        return calibration_results

    def _save_simulations(self, simulations: SimulationData):
        """Save simulation data to file"""
        try:
            with open(self.config.simulations_path, mode="w", encoding="utf-8") as f:
                payload = simulations.model_dump(mode="json", exclude_none=True)
                yaml.dump(payload, f, sort_keys=False, default_flow_style=False)

            self.logger.info(f"Saved simulations to {self.config.simulations_path}")
        except Exception as e:
            self.logger.error(f"Failed to save simulations: {str(e)}")
            raise

    def _save_calibrations(self, calibrations: list[dict]):
        """Save calibration results to file"""
        try:
            # Don't save the full sample arrays to keep file size reasonable
            calibrations_to_save = []
            for cal in calibrations:
                cal_copy = cal.copy()
                # Keep summary statistics but remove full sample array
                if "n_samples" in cal_copy:
                    del cal_copy["n_samples"]
                calibrations_to_save.append(cal_copy)

            with open(self.config.calibrations_path, mode="w", encoding="utf-8") as f:
                yaml.dump(
                    calibrations_to_save, f, sort_keys=False, default_flow_style=False
                )

            self.logger.info(f"Saved calibrations to {self.config.calibrations_path}")
        except Exception as e:
            self.logger.error(f"Failed to save calibrations: {str(e)}")
            raise


# ==============================================================================
# EXAMPLE USAGE
# ==============================================================================

if __name__ == "__main__":
    # Configure custom settings if needed
    print(f'{"/".join(pathlib.Path(__name__).parts[-2:])=}')
    app = AdditiveFOAMCalibration()
    app.configure()
    app.execute()
