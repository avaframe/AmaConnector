"""
    Run script to fetch data of the database
"""

import pathlib
import amaConnector
import grab_demo as gD
import amaUtilities as aU
import avaframeExport as aExport
from avaframe.in3Utils import cfgUtils
from avaframe.in3Utils import logUtils
import avaframe.in3Utils.fileHandlerUtils as fU


# +++++++++SETUP CONFIGURATION++++++++++++++++++++++++
# log file name; leave empty to use default runLog.log
logName = 'runExportEventsData'

# Load avalanche directory and accessFile path from general configuration file
dirPath = pathlib.Path(__file__).parents[0]
cfgMain = cfgUtils.getGeneralConfig(nameFile=(dirPath / 'amaConnectorCfg.ini'))
avalancheDir = pathlib.Path(cfgMain['MAIN']['avalancheDir'])
fU.makeADir(avalancheDir)
accessfile = pathlib.Path(cfgMain['MAIN']['accessFile'])

# Start logging
log = logUtils.initiateLogger(avalancheDir, logName, modelInfo='AmaConnector')
log.info('MAIN SCRIPT')
log.info('Current search: %s', avalancheDir)

# load info on config of fetching data
configuration = cfgMain['MAIN']['dBConfiguration']
eventType = cfgMain['MAIN']['eventType']
constraint = cfgMain['MAIN']['constraint']
projstr = cfgMain['MAIN']['projstr']

# connect to db
amaConnect = amaConnector.amaAccess(accessfile)
log.info('Exporting db using export configuration "%s"' % configuration)
log.info('Type of events is: %s' % eventType)
log.info('Using constraint: %s' % constraint)

# fetch and export all event data for given query
if eventType == 'design':
    useDesignEvents = True
else:
    useDesignEvents = False
eventsRes = aExport.grabEvents(amaConnect, configuration, str(avalancheDir), useDesignEvents, projstr, constraint)
rasterRes = aExport.grabRaster(amaConnect, configuration, str(avalancheDir), useDesignEvents, projstr, constraint)

log.info('Written %d events' % eventsRes)
log.info('Written %d path rasters' % rasterRes)
