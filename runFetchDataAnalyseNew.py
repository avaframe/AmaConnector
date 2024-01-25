"""
    Run script to fetch data of the database
"""

import pathlib
import configparser
import numpy as np
import amaConnector
import grab_demo as gD
import amaUtilities as aU
import matplotlib.pyplot as plt
from shapely import get_coordinates
import matplotlib.patheffects as pe

from avaframe.in3Utils import cfgUtils
from avaframe.in3Utils import logUtils
import avaframe.in3Utils.fileHandlerUtils as fU
import avaframe.in3Utils.geoTrans as gT
import avaframe.out3Plot.amaPlots as aP
import avaframe.in2Trans.ascUtils as IOf
import avaframe.ana5Utils.DFAPathGeneration as DFAPath

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


# test section to identify points along path line
# just experimental code
for index, row in dbFiltered.iterrows():

    # fetch x, y, z coordinats of thalweg line
    x = get_coordinates(row['geom_path_ln3d_epsg:31287_resampled'])[:,0]
    y = get_coordinates(row['geom_path_ln3d_epsg:31287_resampled'])[:,1]

    # fetch DEM
    demPath = pathlib.Path('data', 'amaExports', row['path_name'], ('dem_path_%d.asc' % row['path_id']))
    dem = IOf.readRaster(demPath)

    # setup avaPath to get parabolic fit
    avaPath = {'x': x, 'y': y}
    # first resample path and make smoother - TODO check if required
    avaPath, projPoint = gT.prepareLine(dem, avaPath, distance=cfgMain['MAIN'].getfloat('resamplePathFit'), Point=None)

    # setup config for path generation - for now load from amaConnector main config - TODO use overrides
    DFAPathCfg = cfgMain['PATH']
    # make the parabolic fit
    parabolicFit = DFAPath.getParabolicFit(DFAPathCfg, avaPath, dem)
    # get parabola - use entire path line as base
    sPara = avaPath['s']
    zPara = parabolicFit['a']*sPara*sPara+parabolicFit['b']*sPara+parabolicFit['c']
    # setup parabolicFit dict
    parabolicProfile = {'s': sPara, 'z': zPara}

    # fetch points along thalweg where angle falls below pointAngle
    transitPoint = aU.findAngleInProfile(cfgMain['MAIN'].getfloat('transitPointAngle'), avaPath,
                                       parabolicProfile, cfgMain['MAIN'].getfloat('dsMin'))

    depoPoint = aU.findAngleInProfile(cfgMain['MAIN'].getfloat('depositionPointAngle'), avaPath,
                                         parabolicProfile, cfgMain['MAIN'].getfloat('dsMin'))


    # Do a quadtratic fit
    zQuad = np.polyfit(avaPath['s'], avaPath['z'], 2)
    poly = np.poly1d(zQuad)
    fitProfile = {'s': avaPath['s'], 'z': poly(avaPath['s'])}

    transitPoint2 = aU.findAngleInProfile(cfgMain['MAIN'].getfloat('transitPointAngle'), avaPath,
                                          fitProfile, cfgMain['MAIN'].getfloat('dsMin'))
    depoPoint2 = aU.findAngleInProfile(cfgMain['MAIN'].getfloat('depositionPointAngle'), avaPath,
                                       fitProfile, cfgMain['MAIN'].getfloat('dsMin'))

    # debug figure
    plt.figure()
    plt.title('%s' % row['path_name'])
    plt.plot(avaPath['s'], avaPath['z'], '-y.', label='thalweg',
                 lw=1, path_effects=[pe.Stroke(linewidth=3, foreground='b'), pe.Normal()])

    if transitPoint != '':
        plt.axvline(x=transitPoint['s'], color='lightgrey', linewidth=1, linestyle='-.',
                    label='Transit point %s°' % cfgMain['MAIN']['transitPointAngle'])
        plt.axhline(y=transitPoint['z'], color='lightgrey', linewidth=1, linestyle='-.')
    if depoPoint != '':
        plt.axvline(x=depoPoint['s'], color='grey', linewidth=1, linestyle='-.',
                    label='Deposition point %s°' % cfgMain['MAIN']['depositionPointAngle'])
        plt.axhline(y=depoPoint['z'], color='grey', linewidth=1, linestyle='-.')

    if transitPoint2 != '':
        plt.axvline(x=transitPoint2['s'], color='orange', linewidth=1, linestyle=(0, (5, 10)),
                    label='Transit point fit %s°' % cfgMain['MAIN']['transitPointAngle'])
        plt.axhline(y=transitPoint2['z'], color='orange', linewidth=1, linestyle=(0, (5, 10)))
    if depoPoint2 != '':
        plt.axvline(x=depoPoint2['s'], color='moccasin', linewidth=1, linestyle=(0, (5, 10)),
                    label='Deposition point fit %s°' % cfgMain['MAIN']['depositionPointAngle'])
        plt.axhline(y=depoPoint2['z'], color='moccasin', linewidth=1, linestyle=(0, (5, 10)))
    plt.plot(fitProfile['s'], fitProfile['z'], color='orange', linestyle=':', label='QuadFit')

    plt.xlabel('along thalweg [m]')
    plt.ylabel('elevation [m]')
    plt.plot(sPara, zPara, '-k', label='Parabolic fit')
    plt.legend()
    plt.show()


#++++++++++++++create plots and save dataframe to file
outFile = avalancheDir / 'data.csv'
dbFiltered.to_csv(outFile)

# plot analysis of thalweg in xy and Sxy view
aP.plotPathAngle(dbFiltered, cfgMain, 'rel-runout', 'orig-transit')

# plot histogram of angles for rel-runout travel length
aP.plotHist(dbFiltered, 'rel-runout', cfgMain)

# plot boxplots for angles, travel lengths and altitude drops
aP.plotBoxPlot(dbFiltered, ['rel-runout_Angle', 'orig-depo_Angle', 'orig-transit_Angle'], avalancheDir,
    'angle', renameCols=['alpha', 'beta', 'theta'])
aP.plotBoxPlot(dbFiltered, ['rel-runout_Distance', 'orig-depo_Distance', 'orig-transit_Distance'],
    avalancheDir, 'travel length xy')
aP.plotBoxPlot(dbFiltered, ['rel-runout_LineAltDrop', 'orig-depo_LineAltDrop',
    'orig-transit_LineAltDrop'], avalancheDir, 'altitude drop')
