import shapely
import numpy as np
import pandas as pd

def convert(wkt_text):
    """ converts wkt well known text into z, y, z points """

    # convert using shapely
    p = shapely.wkt.loads(wkt_text)

    return p


def addAlphaAngles(dbData):
    """ filter DF for events that have release point, event point and a path line
        compute angle between release point and event point and add column alpha angle

        Parameters
        -----------
        dbData: pandas dataFrame
            one row per event and all available info for event

        Returns
        ---------
        dbFiltered: pandas dataFrame
            updated dbData with just those events that match filtering criteria
    """


    dbFiltered = dbData[~pd.isnull(dbData['rel_event_pt3d'])]
    dbFiltered['XYDistRelEvent'] = np.empty(len(dbFiltered))
    dbFiltered['ZDistRelEvent'] = np.empty(len(dbFiltered))
    # compute horizontal distance between release point and event point

    for index, eventLine in dbFiltered.iterrows():
        dbFiltered.loc[index,'XYDistRelEvent'] = shapely.distance(convert(dbFiltered.loc[index, 'rel_event_pt']),
            convert(dbFiltered.loc[index,'pt']))
        dbFiltered.loc[index,'ZDistRelEvent'] = convert(dbFiltered.loc[index, 'rel_event_pt3d']).z - convert(dbFiltered.loc[index,'pt3d']).z


    return dbFiltered
