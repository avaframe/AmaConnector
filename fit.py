# -*- coding: utf-8 -*-
"""
Created on Mon Aug 19 10:45:59 2024

@author: LawineNaturgefahren
"""

"""
    Fitting each AMA thalweg within the dataframe according to the choosen fit method
"""

import pathlib
import numpy as np
import amaUtilities as aU
from shapely import get_coordinates
from shapely.geometry import Point, LineString
import math
from sklearn.metrics import r2_score, mean_squared_error

import avaframe.in3Utils.geoTrans as gT
import avaframe.in2Trans.ascUtils as IOf


def fitThalweg (dbData, slope1, slope2, resDist, projstr, dsMin, cfg, fitmethod='all'):
    
    for index, row in dbData.iterrows():

        #coordinates for the whole thalweg profile, extending the O-point
        x = get_coordinates(row['geom_path_ln3d_%s_resampled' % projstr])[:,0]
        y = get_coordinates(row['geom_path_ln3d_%s_resampled' % projstr])[:,1]
    
        # fetch DEM
        demPath = pathlib.Path('data', 'amaExports', row['path_name'], ('dem_path_%d.asc' % row['path_id']))
        dem = IOf.readRaster(demPath)
    
        # setup avaPath to get parabolic fit
        avaPath = {'x': x, 'y': y}
        # first resample path and make smoother - TODO check if required - double resampling check line 56
        avaPath, projPoint = gT.prepareLine(dem, avaPath, distance=resDist, Point=None)

        # TODO: is this resampling to resamplePathFit distance required?
        # it also involves finding the index of the points again on the newly resampled path line
        #crop at origin point - find id of origin on avapath
        oPoint = {'x':[row['geom_origin_pt3d_%s_snapped' % projstr].x], 'y':[row['geom_origin_pt3d_%s_snapped' % projstr].y]}
        origin = gT.findClosestPoint(avaPath['x'], avaPath['y'], oPoint)
        dbData.loc[index, 'origin'] = origin

        #subtract the resolution * the index of origin from the distances, to set origin to distance 0
        avaPath['s'] -= resDist*int(origin)
        avaPathLong = avaPath.copy()
        
        dbData.at[index,'geom_avaPathLong_s_z'] = LineString(list(zip(avaPathLong['s'], avaPathLong['z'])))
        dbData.at[index,'geom_avaPathLong_ln3d_%s_resampled'%projstr] = LineString(list(zip(avaPathLong['x'], avaPathLong['y'], avaPathLong['z'])))
        
        if fitmethod == 'all':
            
            avaPath['x'] = avaPath['x'][origin:]
            avaPath['y'] = avaPath['y'][origin:]
            avaPath['z'] = avaPath['z'][origin:]
            avaPath['s'] = avaPath['s'][origin:]
            
        if fitmethod == 'minz':
            
            minIndex = np.argmin(avaPath['z'])
            avaPath['x'] = avaPath['x'][origin:minIndex]
            avaPath['y'] = avaPath['y'][origin:minIndex]
            avaPath['z'] = avaPath['z'][origin:minIndex]
            avaPath['s'] = avaPath['s'][origin:minIndex]
            
            
        if fitmethod == 'Dmax':
            
            # Crop before origin, to avoid intersection with crop line before that point 
            avaPathCrop = avaPath
            
            #beta angles for crop with thalweg (Dmax)
            m6 = math.tan(math.radians(cfg['MAIN'].getfloat('m6')))
            m5 = math.tan(math.radians(cfg['MAIN'].getfloat('m5')))
            m4 = math.tan(math.radians(cfg['MAIN'].getfloat('m4')))
            m3 = math.tan(math.radians(cfg['MAIN'].getfloat('m3')))
            m2 = math.tan(math.radians(cfg['MAIN'].getfloat('m2')))
            gradients = [m6,m5,m4,m3,m2]
            
            for m in gradients:
                d = aU.calculatetravelLine(m, avaPathCrop, origin)
                intersec = d.intersection(LineString(list(zip(avaPath['s'], avaPath['z']))))
                
                # TODO: why index of 10?
                if intersec.geom_type == 'MultiPoint':
                    endPointID = aU.createCutOff(d, intersec)
                    if endPointID > 10:
                        break
                    
                else: 
                    continue
                
                if endPointID <= 10:
                    endPointID = len(avaPath['s'])
            
            avaPath['x'] = avaPath['x'][origin:]
            avaPath['y'] = avaPath['y'][origin:]
            avaPath['z'] = avaPath['z'][origin:]
            avaPath['s'] = avaPath['s'][origin:]
            
            avaPath['x'] = avaPath['x'][:endPointID]
            avaPath['y'] = avaPath['y'][:endPointID]
            avaPath['z'] = avaPath['z'][:endPointID]
            avaPath['s'] = avaPath['s'][:endPointID]
            
        
        # Do a fit Curve Parabola Fit
        point= {'x':row['geom_origin_pt3d_epsg:31287_snapped'].xy[0], 'y':row['geom_origin_pt3d_%s_snapped' % projstr].xy[1]}
        restraint = gT.findClosestPoint(avaPath['x'], avaPath['y'], point)
        uncertainty = np.zeros(len(avaPath['s'])) + 1.
        uncertainty[restraint] = 0.001
        
        curveProfileLong, curveProfileFit, curvature, b, c = aU.fitCurveParabola(avaPath, avaPathLong, uncertainty) #NOTICE curveProfile z values = z values from avaProfile, zFit = fitted z Values
        curveProfileDictLong = {'s':curveProfileLong['s'],'z':curveProfileLong['zFit']}
        curveProfileDictFit = {'s':curveProfileFit['s'],'z':curveProfileFit['zFit']}
        
        r_squaredcf = r2_score(avaPath['z'], curveProfileDictFit['z'])
        dbData.at[index,'r_squaredcf'] = r_squaredcf
        
        mse = np.square(np.subtract(avaPath['z'], curveProfileDictFit['z'])).mean()
        rmse = math.sqrt(mse)
        dbData.at[index,'rmse'] = rmse

        # TODO: when is the SOI used? is this still required?
        soi1cf = aU.findAngleInProfile(slope1, avaPathLong,
                                              curveProfileDictLong, dsMin)
        soi2cf = aU.findAngleInProfile(slope2, avaPathLong,
                                           curveProfileDictLong, dsMin)
        # Add soi points and avapath, fitted path to dataframe
        if soi1cf != '':
            dbData.at[index,'geom_soi_%s°_cf_pt3d_%s' %(slope1, projstr)] = Point(soi1cf['x'], soi1cf['y'], soi1cf['z'])
            dbData.at[index, 'soi_%s°_s'%slope1] = soi1cf['s']
        
        if soi2cf != '':
            dbData.at[index,'geom_soi_%s°_cf_pt3d_%s' %(slope2, projstr)] = Point(soi2cf['x'], soi2cf['y'], soi2cf['z'])
            dbData.at[index, 'soi_%s°_s'%slope2] = soi2cf['s']
        
        # Fitted path added with z, s coordinates
        # Avapath added with x,y,z as well as another column with z, s
        dbData.at[index, 'geom_avaPath_ln3d_%s_resampled'%projstr]=LineString(list(zip(avaPath['x'], avaPath['y'], avaPath['z'])))
        dbData.at[index, 'avaPath_s_z'] = LineString(list(zip(avaPath['s'], avaPath['z'])))
        dbData.at[index, 'curveFitLong_s_z'] = LineString(list(zip(curveProfileLong['s'], curveProfileLong['zFit'])))
        dbData.at[index, 'curveFit_s_z'] = LineString(list(zip(curveProfileDictFit['s'], curveProfileDictFit['z'])))
        dbData.at[index, 'curvature'] = curvature
        dbData.at[index, 'b'] = b
        dbData.at[index, 'c'] = c
        
    return dbData
        
        