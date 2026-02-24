#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import os
import pandas as pd
import numpy as np


class Path:
    def setSize(self):
        self.size = len(self.data)
        pass

    def setEnd(self):
        self.end = self.data["time"].max()
        pass

    def getIndex(self, time):
        pathIndex = 0
        n = self.size - 1
        if time <= self.end:
            while (pathIndex < n) and (self.data.at[pathIndex, "time"] < time):
                pathIndex += 1
            if (self.data.at[pathIndex, "Mode"] == 1) and (
                self.data.at[pathIndex, "tParam"] == 0
            ):
                pathIndex = min(pathIndex + 1, n)
        else:
            pathIndex = n
        return pathIndex

    def getLocation(self, time):
        # to-do: fix behavior for last time in scan path
        i = self.getIndex(time)
        if time <= self.end:
            dx = self.data.at[i, "xe"] - self.data.at[i, "xs"]
            dy = self.data.at[i, "ye"] - self.data.at[i, "ys"]
            dt = self.data.at[i, "time"] - self.data.at[i - 1, "time"]
            if dt > 0:
                tFrac = (time - self.data.at[i - 1, "time"]) / dt
                dist = [tFrac * dx, tFrac * dy]
            else:
                dist = [0, 0]
            laserCenter = [
                self.data.at[i, "xs"] + dist[0],
                self.data.at[i, "ys"] + dist[1],
            ]
        else:
            laserCenter = [
                self.data.at[self.size - 1, "xs"],
                self.data.at[self.size - 1, "ys"],
            ]
        return [laserCenter, i]

    def loadData(
        self,
        file,
        loadIfExists=None,
        saveFile=True,
        xName="X(mm)",
        yName="Y(mm)",
        timeName="Time(s)",
    ):
        if loadIfExists is not None and os.path.exists(loadIfExists):
            self.data = pd.read_csv(loadIfExists)
            self.setSize()
            self.setEnd()
        else:
            self.data = pd.read_csv(file, sep="\s+")
            self.setSize()
            self.data["time"] = 0.0

            # Load columns from scan path (might have to update righthand side names)
            self.data["xs"] = self.data[xName].to_numpy()
            self.data["xe"] = self.data[xName].to_numpy()
            self.data["ys"] = self.data[yName].to_numpy()
            self.data["ye"] = self.data[yName].to_numpy()
            self.data["tParam"] = self.data[timeName].to_numpy()

            # Calculate time and distance for each point in the scan path
            for index in range(self.size):
                if self.data.at[index, "Mode"] == 1:
                    if index == 0:
                        self.data.at[index, "time"] = self.data.at[index, "tParam"]
                    else:
                        self.data.at[index, "time"] = (
                            self.data.at[index - 1, "time"]
                            + self.data.at[index, "tParam"]
                        )
                    self.data.at[index, "xs"] = self.data.at[index, xName]
                    self.data.at[index, "xe"] = self.data.at[index, xName]
                    self.data.at[index, "ys"] = self.data.at[index, yName]
                    self.data.at[index, "ye"] = self.data.at[index, yName]
                else:
                    if index == 0:
                        assumed_origin = [0.0, 0.0]
                        dx = self.data.at[index, xName] - assumed_origin[0]
                        dy = self.data.at[index, yName] - assumed_origin[1]
                        ts = 0.0
                        xs = assumed_origin[0]
                        ys = assumed_origin[1]
                    else:
                        dx = self.data.at[index, xName] - self.data.at[index - 1, xName]
                        dy = self.data.at[index, yName] - self.data.at[index - 1, yName]
                        ts = self.data.at[index - 1, "time"]
                        xs = self.data.at[index - 1, "xe"]
                        ys = self.data.at[index - 1, "ye"]
                    distance = np.sqrt(np.power(dx, 2) + np.power(dy, 2))
                    # Distance in mm, tParam (velocity) in m/s, time in s
                    self.data.at[index, "time"] = ts + distance / (
                        self.data.at[index, "tParam"] * 1e3
                    )
                    self.data.at[index, "xs"] = xs
                    self.data.at[index, "xe"] = self.data.at[index, xName]
                    self.data.at[index, "ys"] = ys
                    self.data.at[index, "ye"] = self.data.at[index, yName]
            self.setEnd()
            if loadIfExists is not None and saveFile:
                self.data.to_csv(loadIfExists, index=False)

    def get_all_scan_stats(self) -> tuple[float | None, float | None, float, float]:
        """Returns a list summary information about the currently loaded data:

        - elapsed time of the scan path (s)
        - linear distance of the scan path (mm)
        - initial wait time (s)
        - final wait time (s)
        """
        elapsed_time, linear_distance = self.get_elapsed_path_stats()
        initial_wait_time = self.get_initial_wait_time()
        final_wait_time = self.get_final_wait_time()
        return (elapsed_time, linear_distance, initial_wait_time, final_wait_time)

    def get_elapsed_path_stats(self) -> list[float] | list[None]:
        """Extracts the elapsed time (s) and linear distance (mm) of scanning"""

        if self.data is None:
            return [None, None]

        # Elapsed time of scan, in seconds
        elapsed_time = self.data["time"].max()

        # Total path distance, in millimeters
        self.data["path distance"] = np.power(
            np.power(self.data["xe"] - self.data["xs"], 2)
            + np.power(self.data["ye"] - self.data["ys"], 2),
            0.5,
        )
        linear_distance = self.data["path distance"].sum()
        return [float(elapsed_time), float(linear_distance)]

    def _get_spot_offtime(self, row_index) -> float | None:
        """Gets the offtime of a spot melt for the given scan path row index, returns
        None if the given row index is not a spot command with zero power."""
        if self.data is None:
            return None
        if len(self.data) == 0:
            return None
        if row_index < 0:
            row_index = len(self.data) + row_index
        if row_index < 0 or row_index >= len(self.data):
            return None
        if (self.data.at[row_index, "Mode"] == 1) and (
            self.data.at[row_index, "Pmod"] == 0
        ):
            return float(self.data.at[row_index, "tParam"])
        return None

    def get_initial_wait_time(self) -> float:
        """Returns the wait time at the beginning of a scan path"""
        time = self._get_spot_offtime(0)
        return time if time is not None else 0.0

    def get_final_wait_time(self) -> float:
        """Returns the wait time at the end of a scan path"""
        time = self._get_spot_offtime(-1)
        return time if time is not None else 0.0

    data = None
    size = None
    end = None
