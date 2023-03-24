""" functions to fetch data """

import logging
import pathlib

# local imports
import amaUtilities as aU
import amaConnector

# create local logger
log = logging.getLogger(__name__)


def grabAllComplete(outDir, queryString="select * from event_full", accessfile=pathlib.Path('access.txt')):
    """ fetch all event entries of the DB and return a dataFrame with all info for each event

        Parameters
        -----------
        outDir: pathlib path or str
            path where data shall be exported to
        queryString: str
            command to perform query - which entries of the DB shall be fetched
            default is select all entries from available events
        accessfile: pathlib path
            optional - path to access file needed to access database
            a csv-file (including header, seperator: ';') with the following parameters: host, port,
            database, username, password

        Returns
        --------
        dbData: pandas DF
            DF with one row per found event including all available info on event
    """

    # check if accessfile is available
    if not accessfile.is_file():
        message = 'Access file is not a file, check path: %s' % (str(accessfile))
        log.error(message)
        raise FileNotFoundError(message)

    # connect to DB
    amaConnect=amaConnector.amaAccess(accessfile)

    # select all entries according to queryString
    dbData = amaConnect.query(queryString)

    return dbData
