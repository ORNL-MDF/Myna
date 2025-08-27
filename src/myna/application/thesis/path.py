#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import pandas as pd
import numpy as np
import os


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

    data = None
    size = None
    end = None
