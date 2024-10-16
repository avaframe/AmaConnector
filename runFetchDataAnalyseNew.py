"""
    Run script to fetch data of the database, perform analysis for events and plot path analysis and event characteristics summary
"""

import pathlib
import grab_demo as gD
import amaUtilities as aU
import thalwegPlotsMEDIAN as tPM
import fit as fit
import intensityAnalysis as iA

from avaframe.in3Utils import cfgUtils
from avaframe.in3Utils import logUtils
import avaframe.in3Utils.fileHandlerUtils as fU
import avaframe.in3Utils.geoTrans as gT


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
resampleDist = cfgMain['FILTERING'].getfloat('resampleDist')

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

#Import settings from .ini-File
projstr = cfgMain['MAIN']['projstr']
resDist = cfgMain['MAIN'].getfloat('resamplePathFit')
dsMin = cfgMain['MAIN'].getfloat('dsMin')
slope1 = cfgMain['MAIN'].getfloat('slopeAngle1')
slope2 = cfgMain['MAIN'].getfloat('slopeAngle2')

# TODO: this only keeps first event found per path - is this wanted?
# possible implications: for summary plots
mask = dbFiltered.duplicated(subset='path_id', keep ='first')
dbFiltered = dbFiltered[~mask]

# snap release, runout, origin, transit, deposition points to resampled thalweg for all events found that match criteria
dbFiltered = gT.snapPtsToLine(dbFiltered, projstr, lineName='geom_path_ln3d',
    pointsList=[ 'geom_event_pt3d', 'geom_origin_pt3d',
        'geom_transit_pt3d', 'geom_runout_pt3d', 'geom_event_pt3d', 'geom_rel_event_pt3d'])

# compute distance along thalweg between rel- runout, orig-transit, orig-depo
# here the snapped points are chosen also in terms of their elevation on the path line!

dbFiltered = aU.addXYDistAngle(dbFiltered, 'geom_path_ln3d_%s_resampled' % projstr, 'geom_origin_pt3d_%s_snapped' % projstr,
    'geom_transit_pt3d_%s_snapped' % projstr, projstr, name='orig-transit')

dbFiltered = aU.addXYDistAngle(dbFiltered, 'geom_path_ln3d_%s_resampled' % projstr, 'geom_origin_pt3d_%s_snapped' % projstr,
    'geom_runout_pt3d_%s_snapped' % projstr, projstr, name='orig-depo')

dbFiltered = aU.addXYDistAngle(dbFiltered, 'geom_path_ln3d_%s_resampled' % projstr, 'geom_origin_pt3d_%s_snapped' % projstr,
                               'geom_event_pt3d_%s_snapped'% projstr, projstr, name='orig-runout')

# TODO: for now slope angle is computed +-3 points before and after the point of interest if available
# this strongly depends on the chosen resampling distance of the path line! also 3 is hardcoded
dbFiltered = aU.addGradientForPoint(dbFiltered, 'geom_path_ln3d_%s_resampled' % projstr, ['geom_origin_pt3d_%s_snapped' % projstr, 
                                                                                          'geom_transit_pt3d_%s_snapped' % projstr,
                                                                                          'geom_runout_pt3d_%s_snapped' % projstr])

#Calculating intensity characteristics
dbFiltered = iA.intensityCharacteristics(dbFiltered, resDist, cfgMain)
#Applying fit method
dbFiltered = fit.fitThalweg( dbFiltered, slope1, slope2, resDist, projstr, dsMin, cfgMain)

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~~~~~~~~~~~~~~~~~~~~~~SPATIAL CHARACTERISTICS PLOT~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


dist = tPM.plotBoxPlot(dbFiltered, ['orig-transit_Distance', 'orig-depo_Distance' ], avalancheDir, 'length', 
                                 renameY = [r'$s$ [m]', r'$s$ [m]'], ylim=(-500,5000), renameX = ['orig-transit', 'orig-depo'],
                                 renameTitle= ['Distribution of travel length between origin and transit / deposition'+ '\n'])

angle = tPM.plotBoxPlot(dbFiltered, ['orig-transit_Angle', 'orig-depo_Angle' ], avalancheDir, 'angle', 
                                 renameY = [r'$\gamma$[°]'], ylim=(10,60), renameX = ['orig-transit', 'orig-depo'],
                                 renameTitle= ['Distribution of travel angle between origin and transit / deposition'+ '\n'])

altdrop = tPM.plotBoxPlot(dbFiltered, ['orig-transit_LineAltDrop','orig-depo_LineAltDrop' ], avalancheDir, 'altdrop', 
                                 renameY = [r'$z_{s}$ [m]'], ylim=(-50,2000), renameX = ['orig-transit', 'orig-depo'],
                                 renameTitle= ['Distribution of altitude difference between origin and transit / deposition'+ '\n'])


sangle = tPM.plotBoxPlot(dbFiltered, ['geom_origin_pt3d_%s_snapped_gradient' % projstr,
                                     'geom_transit_pt3d_%s_snapped_gradient' % projstr,
                                    'geom_runout_pt3d_%s_snapped_gradient' % projstr], avalancheDir, 'Sangle', 
                                 renameY = [r'$\theta$ [°]'], ylim=(-10, 60),
                                 renameX = [r'$\theta_O$ ', r'$\theta_T$', r'$\theta_D$ '],
                                 renameTitle= ['Distribtion of Slope Angle at Origin, Transit, Deposition point' +'\n'])

tPM.multiplePlots3 ([dist, altdrop, angle, sangle ], 'spatial', '\nSpatial characteristics of Thalweg Analysis\n', avalancheDir)


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~~~~~~~~~~~~~~~~~~INTENSITY CHARACTERISTICS PLOT~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

velocity = tPM.plotBoxPlot(dbFiltered, [ 'velocitiesMax_m/s' ], avalancheDir, 'velocity',
                                 renameY = [r'$v$ [m/s]'],  ylim=(-5,100), renameX = [ r'$v_{max}$'],
                                 renameTitle= ['Distribution of maximum velocities' +'\n'])

destructiveness = tPM.plotBoxPlot(dbFiltered, [ 'destructivnessMax_kPa' ], avalancheDir, 'pressure',
                                 renameY = [r'$P$ [kPa]'],  ylim=(-250,1750),  renameX = [ r'$P_{max}$'],
                                 renameTitle= ['Distribution of maximum destructiveness'+'\n'])

time = tPM.plotBoxPlot(dbFiltered, [ 'times(s)' ], avalancheDir, 'time',
                                 renameY = [r'$t$ [s]'],  ylim=(-5,200), renameX = [ r'$t_D$'],
                                 renameTitle= ['Distribution of travel time'+'\n'])

tPM.multiplePlots2([velocity, destructiveness,  time], 'intensity', '\nIntensity characteristics of Thalweg Analysis\n', avalancheDir)

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~PATH LINE PLOT~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

#ohne Fit
tPM.plotSlopeAngelAnalysis(dbFiltered, 'geom_avaPathLong_ln3d_%s_resampled' % projstr,'geom_avaPathLong_s_z',
                          ['geom_origin_pt3d_%s_snapped'% projstr,
                           'geom_transit_pt3d_%s_snapped' % projstr,
                           'geom_runout_pt3d_%s_snapped' % projstr,
                           'geom_rel_event_pt3d_%s_snapped'% projstr,
                           'geom_event_pt3d_%s_snapped'% projstr],
                            cfgMain, name1='EventNoFit')

#mit Fit
tPM.plotSlopeAngelAnalysis(dbFiltered, 'geom_avaPathLong_ln3d_%s_resampled' % projstr,'geom_avaPathLong_s_z',
                          ['geom_origin_pt3d_%s_snapped'% projstr,
                           'geom_transit_pt3d_%s_snapped' % projstr,
                           'geom_runout_pt3d_%s_snapped' % projstr,
                           'geom_rel_event_pt3d_%s_snapped'% projstr,
                           'geom_event_pt3d_%s_snapped'% projstr],
                            cfgMain, ['curveFitLong_s_z','curveFit_s_z'], name1='EventWtihFit')

#ohne Event mit Fit
tPM.plotSlopeAngelAnalysis(dbFiltered, 'geom_avaPathLong_ln3d_%s_resampled' % projstr,'geom_avaPathLong_s_z',
                          ['geom_origin_pt3d_%s_snapped'% projstr,
                           'geom_transit_pt3d_%s_snapped' % projstr,
                           'geom_runout_pt3d_%s_snapped' % projstr],
                            cfgMain, ['curveFitLong_s_z','curveFit_s_z'], name1='noEventWithFit')

#ohne Event ohne Fit
tPM.plotSlopeAngelAnalysis(dbFiltered, 'geom_avaPathLong_ln3d_%s_resampled' % projstr,'geom_avaPathLong_s_z',
                          ['geom_origin_pt3d_%s_snapped'% projstr,
                           'geom_transit_pt3d_%s_snapped' % projstr,
                           'geom_runout_pt3d_%s_snapped' % projstr],
                            cfgMain, name1='noEventNoFit')

