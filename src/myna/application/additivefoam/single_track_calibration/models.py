#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import logging
import json
import hashlib
from typing import Optional, Annotated, Any
from dataclasses import dataclass
import polars as pl
import numpy as np
from pydantic import BaseModel, model_validator, model_serializer, BeforeValidator


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Utility function for fingerprinting of the model parameters
def create_row_fingerprint(row: dict | pl.Series) -> str:
    """Creates a hash from the process parameters in a DataFrame row"""
    payload = {k: np.round(row[k], 6) for k in ProcessParameters.model_fields.keys()}
    canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode()).hexdigest()


def _ensure_float_list(v: Any) -> list[Any]:
    """Handle floats, lists of floats, and None and convert them all to a list.

    Uses `Any` in the inner list to allow for `None` values
    """
    if v is None:
        return []
    if isinstance(v, (int, float)):
        return [float(v)]
    return list(v)


FlexibleFloatList = Annotated[
    list[Optional[float]], BeforeValidator(_ensure_float_list)
]


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
    depths: Optional[FlexibleFloatList] = None  # in millimeters
    fingerprint: Optional[str] = None

    @model_validator(mode="after")
    def validate_lengths_match(self):
        """Ensure that the length of the `depths` list and the `simulation_parameters.n`
        list are the same, padding `depths` with None values if needed.
        """
        if self.depths is not None:
            max_depths = len(self.simulation_parameters.n)
            if len(self.depths) > max_depths:
                raise ValueError(
                    f"Too many depth values. Found {len(self.depths)}, "
                    f"but only {max_depths} simulation parameters (n) exist."
                )
            elif len(self.depths) < max_depths:
                self.depths.extend([None] * (max_depths - len(self.depths)))
        return self


class ExperimentData(BaseModel):
    """Defines the format of the experimental data file"""

    data: list[SingleTrackData]

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
        # Create dictionary of data
        dicts = [
            {
                **d.process_parameters.model_dump(),
                **d.simulation_parameters.model_dump(),
                "depths": d.depths,
                "fingerprint": d.fingerprint,
            }
            for d in self.data
        ]

        # Explode to get one row per (n, depth) combination
        if len(dicts) == 0:
            df = pl.from_dicts(
                dicts,
                schema={
                    **{k: pl.Float64 for k in ProcessParameters.model_fields},
                    **{k: pl.Float64 for k in SimulationParameters.model_fields},
                    "depths": pl.Float64,
                    "fingerprint": pl.String,
                },
            ).explode(["depths", "n"])
        else:
            df = pl.from_dicts(dicts).explode(["depths", "n"])

        # Add current fingerprint to each row
        param_cols = list(ProcessParameters.model_fields.keys())
        df = df.with_columns(
            pl.struct([pl.col(k) for k in param_cols])
            .map_elements(create_row_fingerprint, return_dtype=pl.String)
            .alias("current_fingerprint")
        )
        return df

    def update_from_df(self, df: pl.DataFrame):
        """Update simulation data from a DataFrame

        Expects df to have one row per n value, with depths as single values
        """
        param_keys = list(ProcessParameters.model_fields.keys())

        # Group by fingerprint to reconstruct records
        grouped = df.group_by("fingerprint").agg(
            [
                *[pl.col(k).first() for k in param_keys],
                pl.col("n").sort(),
                pl.col("depths").sort_by("n"),
            ]
        )

        self.data = [
            SimulatedSingleTrackData(
                process_parameters=ProcessParameters(**{k: r[k] for k in param_keys}),
                simulation_parameters=SimulationParameters(n=r["n"]),
                depths=r["depths"],
                fingerprint=r["fingerprint"],
            )
            for r in grouped.iter_rows(named=True)
        ]


@dataclass
class CalibrationConfig:
    """Configuration for the calibration workflow"""

    experiments_path: str = "test_exp.yaml"
    simulations_path: str = "test_sim.yaml"
    calibrations_path: str = "calibration.yaml"
    simulation_output_dir: str = "sim_output"
    n_values: Optional[list[float]] = None

    def __post_init__(self):
        if self.n_values is None:
            self.n_values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]
