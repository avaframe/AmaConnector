# -*- coding: utf-8 -*-
"""
Created on Thu Nov  9 10:45:02 2023

@author:Magdalena Fischer m09fischer@gmail.com
"""

""" tryOuts Avaframe and AvaConnector"""

import pathlib
import configparser
import numpy as np
import geopandas as gpd
import amaConnector
import grab_demo as gD
import amaUtilities as aU
import shapely
import fiona
from shapely.geometry import LineString
from shapely.geometry import Point
from shapely.wkt import loads
from shapely.wkb import loads as wkb_loads


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
bb = pathlib.Path(cfgMain['MAIN']['bb'])
queryString = cfgMain['MAIN']['queryString']

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

# snap release, runout, origin, transit, deposition points to resampled thalweg for all events found that match criteria
dbFiltered = gT.snapPtsToLine(dbFiltered, cfgMain['MAIN']['projstr'], lineName='geom_path_ln3d',
    pointsList=['geom_rel_event_pt3d', 'geom_event_pt3d', 'geom_origin_pt3d',
        'geom_transit_pt3d', 'geom_runout_pt3d'])

# compute distance along thalweg between rel- runout, orig-transit, orig-depo
# here the snapped points are chosen also in terms of their elevation on the path line!
projstr = cfgMain['MAIN']['projstr']
dbFiltered = aU.addXYDistAngle(dbFiltered, 'geom_path_ln3d_%s_resampled' % projstr, 'geom_rel_event_pt3d_%s_snapped' % projstr,
    'geom_event_pt3d_%s_snapped' % projstr, projstr, name='rel-runout')

dbFiltered = aU.addXYDistAngle(dbFiltered, 'geom_path_ln3d_%s_resampled' % projstr, 'geom_origin_pt3d_%s_snapped' % projstr,
    'geom_transit_pt3d_%s_snapped' % projstr, projstr, name='orig-transit')

dbFiltered = aU.addXYDistAngle(dbFiltered, 'geom_path_ln3d_%s_resampled' % projstr, 'geom_origin_pt3d_%s_snapped' % projstr,
    'geom_runout_pt3d_%s_snapped' % projstr, projstr, name='orig-depo')

#loading bounding Box from gpkg file from ini file
bbFile = gpd.read_file(str(dirPath)+'/'+ str(bb))



#function for checking if event point is within the bounding box, bBboxGeometry as Dataframe, pointGeometry as geometry.point.Point
def isWithinBoundingBox(bBoxGeometry, pointGeometry):
    return pointGeometry.within(bBoxGeometry)

dbDataFiltered = dbData[dbData['geom_rel_event_ln'].notna()]
#transforming geom_event_pt column ito a geometry, currently WGS84 data used
dbDataFiltered['geom_event_pt'] = dbDataFiltered['geom_event_pt'].apply(wkb_loads)

# Apply the function to create a new column 'AOI' in your dbData to verify if the point is within aoi. currently WGS84 used, to change choose different column
#remeber to provide aoi file in the same projection
dbDataFiltered['AOI'] = dbDataFiltered.apply(lambda row: isWithinBoundingBox( bbFile['geometry'].iloc[0], row['geom_event_pt']), axis=1)

aoiList = dbDataFiltered.loc[dbDataFiltered['AOI'], 'event_id'].tolist()
aoiFiltered = dbDataFiltered[dbDataFiltered['AOI']]


#single Event path extract und export
#selecting relevant ID's createing emty Dataframe
#listAOI = [590,786,788,787,793,912,913,914,915,916]
exportDataRelLn = gpd.GeoDataFrame(columns=['event_id'])
exportDataPathLn = gpd.GeoDataFrame(columns=['event_id'])

#Looping through ID List transforming lineString for geom:event_ln to geometry column and adding to empty Dataframe

for i in aoiFiltered['event_id']:
    
    singleEvent = dbFiltered.loc[dbFiltered['event_id']== i]
    singleEvent=gpd.GeoDataFrame(singleEvent)
    

    
    coordsRelEventLn = singleEvent['geom_rel_event_ln'].geometry.apply(lambda geom: list(geom.coords))
    geometryRelLn = coordsRelEventLn.apply(lambda coords: LineString(coords))
    geoDfRelLn = gpd.GeoDataFrame(geometry=geometryRelLn)
    geoDfRelLn = geoDfRelLn.assign(event_id = i)
    exportDataRelLn = exportDataRelLn.append([geoDfRelLn])
    
    
    coordsPathLn = singleEvent['geom_path_ln'].geometry.apply(lambda geom: list(geom.coords))
    geometryPathLn = coordsPathLn.apply(lambda coords: LineString(coords))
    geoDfPathLn = gpd.GeoDataFrame(geometry=geometryPathLn)
    geoDfPathLn = geoDfPathLn.assign(event_id = i)
    exportDataPathLn = exportDataPathLn.append([geoDfPathLn])
    
#Export of Dataframe based on ID List 

output_geopackage_path = 'C:/Users/LawineNaturgefahren/MagdalenaTest/testArea1/rel_ln.gpkg'
exportDataRelLn.to_file(output_geopackage_path, driver='GPKG')

output_geopackage_path = 'C:/Users/LawineNaturgefahren/MagdalenaTest/testArea1/path_ln.gpkg'
exportDataPathLn.to_file(output_geopackage_path, driver='GPKG')

