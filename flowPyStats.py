# -*- coding: utf-8 -*-
"""
Created on Tue Nov 28 11:07:08 2023

@author: LawineNaturgefahren
"""

import pathlib
import configparser
import numpy as np
import amaConnector
import grab_demo as gD
import amaUtilities as aU
import geopandas as gpd
import pandas as pd
import rasterio
from rasterio import mask
from rasterio import features
from shapely.geometry import Point
from shapely.ops import cascaded_union
from shapely.geometry import Polygon
from rasterio.features import shapes
from shapely.geometry import shape
from rasterio.features import geometry_mask
from shapely.geometry import mapping
from shapely.wkt import loads
from pprint import pprint
import matplotlib.pyplot as plt

from avaframe.in3Utils import cfgUtils
from avaframe.in3Utils import logUtils
import avaframe.in3Utils.fileHandlerUtils as fU
import avaframe.in3Utils.geoTrans as gT
import avaframe.out3Plot.amaPlots as aP

# +++++++++SETUP CONFIGURATION++++++++++++++++++++++++
# log file name; leave empty to use default runLog.log
logName = 'runFetchDataAnalyse'

# Load avalanche directory and accessFile path from general configuration file
dirPath = pathlib.Path(__file__).parents[0]
cfgMain = cfgUtils.getGeneralConfig(nameFile=(dirPath / 'amaConnectorCfg.ini'))
avalancheDir = pathlib.Path(cfgMain['MAIN']['avalancheDir'])
fU.makeADir(avalancheDir)
accessfile = pathlib.Path(cfgMain['MAIN']['accessFile'])
queryString = cfgMain['MAIN']['queryString']
travel = cfgMain['MAIN']['travel']
angle = cfgMain['MAIN']['angle']
flux = cfgMain['MAIN']['flux']
dem = cfgMain['MAIN']['dem']


# load info on setup for analysis
nonEmptyCols = cfgMain['FILTERING']['nonEmptyAttributes'].split('|')
addAttributes = cfgMain['FILTERING']['addAttributes'].split('|')
resampleDist =  cfgMain['FILTERING'].getfloat('resampleDist')

# Start logging
log = logUtils.initiateLogger(avalancheDir, logName, modelInfo='AmaConnector')
log.info('MAIN SCRIPT')
log.info('Current search: %s', avalancheDir)

# fetch all info of the database according to queryString and return dataFrame
dbData = gD.grabAllComplete(avalancheDir, queryString=queryString, accessfile=accessfile)
log.info('Fetched %d entries from data base ' % (len(dbData)))
for index, row in dbData.iterrows():
    log.info('%s, event id: %s, index %s' % (row['path_name'], row['event_id'], index))

# filter db according to nonEmptyCols and convert geometry entries to desired projection
# resample thalweg for higher resolution
dbFiltered = aU.fetchGeometryInfo(dbData, 'epsg:4326', cfgMain['MAIN']['projstr'],
    cfgMain['FILTERING']['geomStr'], nonEmptyCols, addAttributes, resampleDist)

log.info('Filtered db data and converted to %s' % cfgMain['MAIN']['projstr'])
log.info('Events found for path name:')
for index, row in dbFiltered.iterrows():
    log.info('%s, event id: %s' % (row['path_name'], row['event_id']))


with rasterio.open(flux) as fluxRaster:
    fluxData= fluxRaster.read(1).astype('float32')
    fluxData[fluxData == -9999] = np.nan
    transformFlux= fluxRaster.transform

#identifying release cells
#maskFlux = fluxData == 1

#identify avalanche
maskFlux = fluxData !=0
polygons = list(shapes(fluxData, mask = maskFlux, transform=transformFlux))
fluxPoly = gpd.GeoDataFrame(geometry=[shape(s) for s,v in polygons])

#dissolving the neighbouring pixels to polygons, first one multpolygon, then splitting into single polygons. 
#only pixels which are connected via a side are dissolved, cornering pixels stay seperat
#TODO resolve crs! even though assingning one, none is shown in qgis, has to be assigned manually there again
fluxPoly['buffer'] = fluxPoly['geometry'].buffer(1)
dissolvedGeom = cascaded_union(fluxPoly['buffer'])
dissolvedPoly = gpd.GeoDataFrame(geometry=[dissolvedGeom])
dissolvedPoly = dissolvedPoly.explode()
dissolvedPoly.crs = cfgMain['MAIN']['projstr']
dbFiltered = gpd.GeoDataFrame(dbFiltered, geometry = dbFiltered['geom_rel_event_pt_epsg:31287'])
dbFiltered.set_geometry('geom_rel_event_pt_epsg:31287')
joined = gpd.sjoin(dissolvedPoly, dbFiltered, how='left', op= 'contains')
joined = joined.rename(columns={'geometry': 'geom_simulatedPolygons'})
emptygeom = gpd.GeoDataFrame(columns=None, geometry=gpd.GeoSeries())
joined['geom_fp_runout_pt3d_travel_epsg:31287'] = emptygeom
joined['geom_fp_runout_pt3d_angle_epsg:31287'] = emptygeom
joined.set_geometry('geom_simulatedPolygons')

#dissolvedPoly.to_file(r'C:\Users\LawineNaturgefahren\MagdalenaTest\AmaConnector\data\amaExports\testPolyFlux.gpkg', driver='GPKG')

for index, row in joined.iterrows():
    geometry = row['geom_simulatedPolygons']
    
    #Open rasterfiles from flowpy Calculation and Dem used as input for calculation
    with rasterio.open(travel) as travelRaster:
        travelData= travelRaster.read(1).astype('float32')
        maskTravel = features.geometry_mask([geometry], out_shape=travelRaster.shape, transform=travelRaster.transform, invert = True)
        maskedTravel = np.where(maskTravel, travelData, np.nan)
        maskedTravel = np.ma.masked_invalid(maskedTravel)
        
        #travelData[travelData == 0] = np.nan
        maxIndices = np.unravel_index(np.argmax(maskedTravel), maskedTravel.shape)
        maxValue = maskedTravel[maxIndices]
        #minIndices = np.unravel_index(np.nanargmin(travelData), travelData.shape)
        #minValue = travelData[minIndices]
        lon, lat = travelRaster.xy(maxIndices[0],maxIndices[1])
        runoutPtTravel = gpd.GeoDataFrame({'MaxLength': [maxValue]},  geometry=[Point(lon, lat)], crs=cfgMain['MAIN']['projstr'])
        
        #runoutPtTravel['MinLength']
    '''
        geometry = dissolvedPoly.geometry.values[0]
        transform = travelRaster.transform
        out_shape = travelRaster.shape
        maskTravel = features.geometry_mask([geometry], out_shape=out_shape, transform=transform)
        maskedTravel = np.where(maskTravel, np.nan, travelData)
    
    
    
        
        maskTravel, _ = mask.mask(travelRaster, [geometry], invert=True, nodata=np.nan)
        maskTravel=maskTravel[0]
        print(np.nanmin(maskTravel))
        maskedTravel = np.where(np.isnan(maskTravel), np.nan, travelData)
        maskedTravel = maskedTravel[0]
        
        minIndices = np.unravel_index(np.nanargmin(maskedTravel), maskedTravel.shape)
        minValue = maskedTravel[minIndices]
    '''

    # Set values outside the polygon to NaN in the raster array
    #raster_array[mask] = np.nan
    #Open rasterfiles from flowpy Calculation and Dem used as input for calculation
    with rasterio.open(angle) as angleRaster:
        angleData = angleRaster.read(1).astype('float32')
        maskAngle = features.geometry_mask([geometry], out_shape=angleRaster.shape, transform=angleRaster.transform, invert = True)
        maskedAngle = np.where(maskAngle, angleData, np.nan)
        maskedAngle [maskedAngle == 0] =np.nan
        maskedAngle = np.ma.masked_invalid(maskedAngle)
        
        
        #angleData[angleData == 0] = np.nan
        #minValue = np.nanmin(angleData)
        minIndices = np.unravel_index(np.nanargmin(maskedAngle), maskedAngle.shape)
        minValue = angleData[minIndices]
        lon, lat = angleRaster.xy(minIndices[0],minIndices[1])
        runoutPtAngle = gpd.GeoDataFrame({'MinAngle': [minValue]}, geometry=[Point(lon, lat)], crs=cfgMain['MAIN']['projstr'])
        
    with rasterio.open(dem) as demRaster:
        # Read the DEM data as a NumPy array
        demData = demRaster.read(1).astype('float32')
        demData[demData == 0] = np.nan
        
        for ind, point in runoutPtAngle.iterrows():
            lon, lat = point['geometry'].x, point['geometry'].y
            elevationValue = list(demRaster.sample([(lon,lat)]))
            if elevationValue:
                elevationValue =elevationValue[0]
                point3d = Point(lon,lat,elevationValue[0])
                #runoutPtAngle.at[index, 'geom_fp_runout_pt3d_angle_epsg:31287']=point3d
                joined.loc[index, 'geom_fp_runout_pt3d_angle_epsg:31287'] =point3d
                
        for ind, point in runoutPtTravel.iterrows():
            lon, lat = point['geometry'].x, point['geometry'].y
            eleValue = list(demRaster.sample([(lon,lat)]))
            if eleValue:
                eleValue =eleValue[0]
                point3d = Point(lon,lat,eleValue[0])
                #runoutPtTravel.at[index, 'geom_fp_runout_pt3d_travel_epsg:31287']=point3d
                joined.loc[index, 'geom_fp_runout_pt3d_travel_epsg:31287'] = point3d
        
'''   
#TODO event_id single event at the moment hardcoded, maybe it can be extracted through the release point 
runoutPtAngle['event_id'] = 913   
runoutPtTravel['event_id'] = 913

dbFiltered = pd.merge(dbFiltered, runoutPtTravel[['geom_fp_runout_pt3d_travel_epsg:31287','event_id']], on='event_id')
dbFiltered = pd.merge(dbFiltered, runoutPtAngle[['geom_fp_runout_pt3d_angle_epsg:31287','event_id']], on='event_id')
'''
dbFiltered = joined
#dbFiltered['geom_fp_runout_pt3d_travel_epsg:31287'].crs = 'EPSG:31287'
#dbFiltered['geom_fp_runout_pt3d_angle_epsg:31287'].crs = 'EPSG:31287'
# snap release, runout, origin, transit, deposition points to resampled thalweg for all events found that match criteria
dbFiltered = gT.snapPtsToLine(dbFiltered, cfgMain['MAIN']['projstr'], lineName='geom_path_ln3d',
    pointsList=['geom_rel_event_pt3d', 'geom_event_pt3d', 'geom_origin_pt3d',
        'geom_transit_pt3d', 'geom_runout_pt3d','geom_fp_runout_pt3d_travel', 'geom_fp_runout_pt3d_angle'])

# compute distance along thalweg between rel- runout, orig-transit, orig-depo
# here the snapped points are chosen also in terms of their elevation on the path line!
projstr = cfgMain['MAIN']['projstr']
dbFiltered = aU.addXYDistAngle(dbFiltered, 'geom_path_ln3d_%s_resampled' % projstr, 'geom_rel_event_pt3d_%s_snapped' % projstr,
    'geom_event_pt3d_%s_snapped' % projstr, projstr, name='rel-runout')

dbFiltered = aU.addXYDistAngle(dbFiltered, 'geom_path_ln3d_%s_resampled' % projstr, 'geom_rel_event_pt3d_%s_snapped' % projstr,
    'geom_fp_runout_pt3d_angle_%s_snapped' % projstr, projstr, name='rel-fpAngleRunout')

dbFiltered = aU.addXYDistAngle(dbFiltered, 'geom_path_ln3d_%s_resampled' % projstr, 'geom_rel_event_pt3d_%s_snapped' % projstr,
    'geom_fp_runout_pt3d_travel_%s_snapped' % projstr, projstr, name='rel-fpTravelRunout')

dbFiltered = aU.addXYDistAngle(dbFiltered, 'geom_path_ln3d_%s_resampled' % projstr, 'geom_origin_pt3d_%s_snapped' % projstr,
    'geom_transit_pt3d_%s_snapped' % projstr, projstr, name='orig-transit')

dbFiltered = aU.addXYDistAngle(dbFiltered, 'geom_path_ln3d_%s_resampled' % projstr, 'geom_origin_pt3d_%s_snapped' % projstr,
    'geom_runout_pt3d_%s_snapped' % projstr, projstr, name='orig-depo')


# plot analysis of thalweg in xy and Sxy view
aP.plotPathAngle(dbFiltered, cfgMain, 'rel-runout', 'orig-transit')

# plot histogram of angles for rel-runout travel length
aP.plotHist(dbFiltered, 'rel-runout', cfgMain)

# plot boxplots for angles, travel lengths and altitude drops
aP.plotBoxPlot(dbFiltered, ['rel-runout_Angle', 'rel-fpAngleRunout_Angle', 'rel-fpTravelRunout_Angle', 'orig-depo_Angle', 'orig-transit_Angle'], avalancheDir,
    'angle', renameCols=['alpha(rel_runout)', 'alpha2(rel_runoutfp_minAngle)', 'alpha3(rel_runoutfp_maxTravel)','beta(orig_depo)', 'theta(orig_transit)'])

aP.plotBoxPlot(dbFiltered, ['rel-runout_Distance', 'rel-fpAngleRunout_Distance', 'rel-fpTravelRunout_Distance', 'orig-depo_Distance', 'orig-transit_Distance'],
    avalancheDir, 'travel length xy')

aP.plotBoxPlot(dbFiltered, ['rel-runout_LineAltDrop', 'rel-fpAngleRunout_LineAltDrop', 'rel-fpTravelRunout_LineAltDrop', 'orig-depo_LineAltDrop',
    'orig-transit_LineAltDrop'], avalancheDir, 'altitude drop')


