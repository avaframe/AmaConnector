import pathlib
import configparser
import numpy as np
import amaConnector
import grab_demo as gD
import amaUtilities as aU
import geopandas as gpd
from shapely.geometry import Point
from shapely.wkt import loads


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

#dbElevation = gpd.GeoDataFrame(dbData[['pt3d', 'event_id']])
#heights = dbElevation.apply(lambda z: z[2])
#heights = loads(heights[0])
#heights = heights.z


#function to extract the Z coordinate from a Point geometry
def get_z_coordinate(point):
    point = loads(point)
    return point.z

# Apply the function to create a new column 'z_coordinate' in your DataFrame
dbFiltered['zCoordinate'] = dbFiltered['geom_event_pt3d'].apply(lambda point: point.z)
#dbData['zCoordinate'] = dbData['pt3d'].apply(get_z_coordinate)
#dbData['zCoordinate'] = dbData['pt3d'].apply(get_z_coordinate)
#dbElevation['z_coordinate'] = dbElevation['pt3d'].apply(get_z_coordinate)

#elev500 = dbFiltered[dbFiltered['zCoordinate']<=500]
elev1000 = dbFiltered[(dbFiltered['zCoordinate']>500) & (dbFiltered['zCoordinate']<= 1000)]
elev1500 = dbFiltered[(dbFiltered['zCoordinate']>1000) & (dbFiltered['zCoordinate']<= 1500)]
elev2000 = dbFiltered[(dbFiltered['zCoordinate']>1500) & (dbFiltered['zCoordinate']<= 2000)]
elev2500 = dbFiltered[(dbFiltered['zCoordinate']>2000) & (dbFiltered['zCoordinate']<= 2500)]
elev3000 = dbFiltered[dbFiltered['zCoordinate']>=3000]


#++++++++++++++create plots and save dataframe to file
outFile = avalancheDir / 'data.csv'
dbFiltered.to_csv(outFile)

# plot analysis of thalweg in xy and Sxy view
#aP.plotPathAngle(dbFiltered, cfgMain, 'rel-runout', 'orig-transit')

# plot histogram of angles for rel-runout travel length
#aP.plotHist(dbFiltered, 'rel-runout', cfgMain)

# plot boxplots for angles, travel lengths and altitude drops
aP.plotBoxPlot(elev1000, ['rel-runout_Angle', 'orig-depo_Angle', 'orig-transit_Angle'], avalancheDir,
    'angle', renameCols=['alpha', 'beta', 'theta'])
aP.plotBoxPlot(elev1000, ['rel-runout_Distance', 'orig-depo_Distance', 'orig-transit_Distance'],
    avalancheDir, 'travel length xy')
aP.plotBoxPlot(elev1000, ['rel-runout_LineAltDrop', 'orig-depo_LineAltDrop',
    'orig-transit_LineAltDrop'], avalancheDir, 'altitude drop')

aP.plotBoxPlot(elev1500, ['rel-runout_Angle', 'orig-depo_Angle', 'orig-transit_Angle'], avalancheDir,
    'angle', renameCols=['alpha', 'beta', 'theta'])
aP.plotBoxPlot(elev1500, ['rel-runout_Distance', 'orig-depo_Distance', 'orig-transit_Distance'],
    avalancheDir, 'travel length xy')
aP.plotBoxPlot(elev1500, ['rel-runout_LineAltDrop', 'orig-depo_LineAltDrop',
    'orig-transit_LineAltDrop'], avalancheDir, 'altitude drop')

aP.plotBoxPlot(elev2000, ['rel-runout_Angle', 'orig-depo_Angle', 'orig-transit_Angle'], avalancheDir,
    'angle', renameCols=['alpha', 'beta', 'theta'])
aP.plotBoxPlot(elev2000, ['rel-runout_Distance', 'orig-depo_Distance', 'orig-transit_Distance'],
    avalancheDir, 'travel length xy')
aP.plotBoxPlot(elev2000, ['rel-runout_LineAltDrop', 'orig-depo_LineAltDrop',
    'orig-transit_LineAltDrop'], avalancheDir, 'altitude drop')

aP.plotBoxPlot(elev2500, ['rel-runout_Angle', 'orig-depo_Angle', 'orig-transit_Angle'], avalancheDir,
    'angle', renameCols=['alpha', 'beta', 'theta'])
aP.plotBoxPlot(elev2500, ['rel-runout_Distance', 'orig-depo_Distance', 'orig-transit_Distance'],
    avalancheDir, 'travel length xy')
aP.plotBoxPlot(elev2500, ['rel-runout_LineAltDrop', 'orig-depo_LineAltDrop',
    'orig-transit_LineAltDrop'], avalancheDir, 'altitude drop')

aP.plotBoxPlot(elev3000, ['rel-runout_Angle', 'orig-depo_Angle', 'orig-transit_Angle'], avalancheDir,
    'angle', renameCols=['alpha', 'beta', 'theta'])
aP.plotBoxPlot(elev3000, ['rel-runout_Distance', 'orig-depo_Distance', 'orig-transit_Distance'],
    avalancheDir, 'travel length xy')
aP.plotBoxPlot(elev3000, ['rel-runout_LineAltDrop', 'orig-depo_LineAltDrop',
    'orig-transit_LineAltDrop'], avalancheDir, 'altitude drop')
