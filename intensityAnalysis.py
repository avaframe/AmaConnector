# -*- coding: utf-8 -*-

"""
Created on Tue Aug 20 10:56:31 2024

@author: LawineNaturgefahren
"""

"""
Intensity characteristics AMA thalwege
"""

import math
import pathlib

import avaframe.in2Trans.ascUtils as IOf
import avaframe.in3Utils.geoTrans as gT
import numpy as np
from shapely import get_coordinates


def intensityCharacteristics(dbData, resDist, cfg):

    for index, row in dbData.iterrows():

        # total length of thalweg
        x = get_coordinates(
            row["geom_path_ln3d_%s_resampled" % cfg["MAIN"]["projstr"]]
        )[:, 0]
        y = get_coordinates(
            row["geom_path_ln3d_%s_resampled" % cfg["MAIN"]["projstr"]]
        )[:, 1]

        # fetch DEM
        demPath = pathlib.Path(
            "data", "amaExports", row["path_name"], ("dem_path_%d.asc" % row["path_id"])
        )
        dem = IOf.readRaster(demPath)

        # setup avaPath to get parabolic fit
        avaPath = {"x": x, "y": y}
        # first resample path and make smoother - TODO check if required - double resampling check line 56
        avaPath, projPoint = gT.prepareLine(dem, avaPath, distance=resDist, Point=None)

        # TODO: is this resampling to resamplePathFit distance required?
        # it also involves finding the index of the points again on the newly resampled path line
        opoint = {
            "x": row["geom_origin_pt3d_%s_snapped" % cfg["MAIN"]["projstr"]].xy[0],
            "y": row["geom_origin_pt3d_%s_snapped" % cfg["MAIN"]["projstr"]].xy[1],
        }
        origin = gT.findClosestPoint(avaPath["x"], avaPath["y"], opoint)

        tpoint = {
            "x": row["geom_transit_pt3d_%s_snapped" % cfg["MAIN"]["projstr"]].xy[0],
            "y": row["geom_transit_pt3d_%s_snapped" % cfg["MAIN"]["projstr"]].xy[1],
        }
        transit = gT.findClosestPoint(avaPath["x"], avaPath["y"], tpoint)

        dpoint = {
            "x": row["geom_runout_pt3d_%s_snapped" % cfg["MAIN"]["projstr"]].xy[0],
            "y": row["geom_runout_pt3d_%s_snapped" % cfg["MAIN"]["projstr"]].xy[1],
        }
        depo = gT.findClosestPoint(avaPath["x"], avaPath["y"], dpoint)

        dbData.at[index, "depoID"] = depo
        dbData.at[index, "transitID"] = transit
        dbData.at[index, "origID"] = origin

        # Velocity Z(δ) =  Z(O) - Z(S) - S * (Z(O)-Z(Min))/S(Min)
        # Vmax = √(Z(δ)max ∗2g)

        sxy = avaPath["s"][origin:depo]
        z = avaPath["z"][origin:depo]
        ds = np.diff(sxy)
        dz = np.diff(z)

        zO = z[0]
        zD = z[-1]
        sD = sxy[-1]

        velocities_kmh = []
        velocities_ms = []
        velocities_kPa = []
        times = []

        for i, dist in enumerate(sxy):

            zdelta = abs(zO - z[i] - sxy[i] * ((zO - zD) / sD))
            veloc = math.sqrt(zdelta * 2.0 * cfg["MAIN"].getfloat("g"))
            velocities_ms.append(veloc)
            velocities_kmh.append(veloc * 3.6)
            velocities_kPa.append(
                ((veloc**2.0) * cfg["MAIN"].getfloat("density")) / 1000.0
            )

            if i < len(dz):
                if veloc == 0:
                    continue
                else:
                    if len(velocities_ms) > 1:
                        v1 = velocities_ms[-1]
                        v2 = velocities_ms[-2]
                        mv = 1 / 2 * (v2 + v1)
                        dsxyz = math.sqrt(dz[i] ** 2 + ds[i] ** 2)
                        time = dsxyz / mv
                        times.append(time)

                    else:
                        dsxyz = math.sqrt(dz[i] ** 2 + ds[i] ** 2)
                        time = dsxyz / veloc
                        times.append(time)

        cumTimes = np.cumsum(times)

        dbData.at[index, "velocitiesMax_km/h"] = max(velocities_kmh)
        dbData.at[index, "velocitiesMax_m/s"] = max(velocities_ms)
        dbData.at[index, "destructivnessMax_kPa"] = max(velocities_kPa)

        """
        dbData.at[index,'velocitiesT_km/h'] = velocities_kmh[transit-1]
        dbData.at[index,'velocitiesT_m/s'] = velocities_ms[transit-1]
        dbData.at[index,'destructivnessT_kPa'] = velocities_kPa[transit]
        """

        if len(cumTimes) > 1:
            dbData.at[index, "times(s)"] = cumTimes[-1]

    return dbData
