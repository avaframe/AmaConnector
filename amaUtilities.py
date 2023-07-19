from shapely import wkb, LineString, Point, length
from shapely.ops import split
import numpy as np
import pandas as pd
import geopandas
import avaframe.in3Utils.geoTrans as gT


def fetchGeometryInfo(dbData, srcprojstr, projstr, geomStr, nonEmptyCols, addAttributes, resampleDist):
    """ filter DF for events where non null columns for nonEmptyCols
        transform all columns that have geomStr in it to desired crs defined by projstr
        resample path_ln3d with resampleDist
        return filtered DF with geomStr columns and addAttributes columns

        Parameters
        -----------
        dbData: pandas dataFrame
            one row per event and all available info for event
        srcprojstr: str
            name source projection
        projstr: str
            name of desired projection
        geomStr: str
            search substring that geometry columns must contain
        nonEmptyCols: list
            filter dbData for columns that have non null value for these cols
        addAttributes: list
            attributes that shall be added to dbFiltered geometry info from dbData
        resampleDist: float
            distance of resampling along path line

        Returns
        ---------
        dbFiltered: pandas dataFrame
            data frame with just those events that match non null entries for nonEmptyCols
            and transformed geometry info in desired crs (projstr), resampled path_ln3d and addAttributes
    """

    # fetch info on desired crs
    crsVal = projstr.split('epsg:')[1]

    # filter DF for nonEmptyCols
    for nECol in nonEmptyCols:
        dbFiltered = dbData[~pd.isnull(dbData[nECol])]

    # filter DF for all geometry columns
    dbFilteredGeom = dbFiltered.filter(regex=geomStr).copy()

    # loop over all geom cols and transform geometry to projstr
    for col in dbFilteredGeom.columns:
        convertedGeo = dbFilteredGeom[col].apply(wkb.loads, hex=True)
        dbFilteredGeom.loc[:,col] = convertedGeo
        gdf = geopandas.GeoDataFrame(dbFilteredGeom, geometry=col, crs=srcprojstr)
        gdfConvert = gdf.to_crs(epsg=crsVal)
        dbFilteredGeom.insert(0, (col + '_' + projstr), gdfConvert[col])

    # resample path line to get higher resolution
    lineResampled = []
    dbFilteredGeom['pathLength'] = np.empty(len(dbFilteredGeom))
    for index, row in dbFilteredGeom.iterrows():
        line = row['geom_path_ln3d_' + projstr]
        distInt = int(np.ceil(line.length / resampleDist))
        distances = np.linspace(0, line.length, distInt)
        lineR = LineString([line.interpolate(dist) for dist in distances])
        lineResampled.append(lineR)
        dbFilteredGeom.loc[index, 'pathLength'] = length(line)

    # append resampled path line as column
    dbFilteredGeom.insert(0, 'geom_path_ln3d_%s_resampled' % projstr, lineResampled)

    # add desired attributes form dbData
    dbFilteredGeom = dbFilteredGeom.join(dbFiltered[addAttributes])

    return dbFilteredGeom


def addXYDistAngle(dbData, line, point1, point2, projstr, name='event'):
    """ compute the distance along line between point1 and point 2 and angle of this part of the line

        Parameters
        -----------
        dbData: pandas dataframe
            dataframe with geometry info of events
        line: str
            name of line column
        point1: str
            name of starting point column
        point2: str
            name of ending point column
        projstr: str
            name of projection
        name: str
            name of line and angle

        Returns
        --------
        dbData: pandas dataframe
            dataframe with geometry info of events updated with xyDistance
    """

    dbData['%s_Distance' % name] = np.empty(len(dbData))
    dbData['%s_LineStart' % name] = np.empty(len(dbData))
    dbData['%s_LineAltDrop' % name] = np.empty(len(dbData))
    dbData['%s_xyLine' % name] = np.empty(len(dbData))
    dbData['%s_xyAngle' % name] = np.empty(len(dbData))
    dbData['%s_xyPathDist' % name] = np.empty(len(dbData))

    distancePath = []
    distanceEvent = []
    for index, row in dbData.iterrows():
        # first split the line using point1 and use second line segment (from point1 onwards)
        line1 = split(row[line], row[point1])
        # check if point1 is located right at the start of the line - so when splitting line no effect
        if len[line1.geoms] == 1 and line1.boundary.geoms[0] == point1:
            line1 = line1.geoms[0]
        else:
            # if point1 is located further down the line take the part of the line from the point1 onwards
            line1 = line1.geoms[1]
        # the split this line segment using point2 and use first line segment
        # resulting line2 is the line segment between point1 and point2
        line2 = split(line1, row[point2]).geoms[0]
        dbData.loc[index, '%s_Distance' % name] = length(line2)
        dbData.loc[index, '%s_Line' % name] = line2
        dbData.loc[index, '%s_LineStart' % name] = length(split(row[line], row[point1]).geoms[0])
        elevationDrop = row[point1].z - row[point2].z
        dbData.loc[index, '%s_Angle' % name] = np.rad2deg(np.arctan(elevationDrop / length(line2)))
        dbData.loc[index, '%s_LineAltDrop' % name] = elevationDrop
        # compute path segment lengths and cumulative length
        distP = gT.computeAlongLineDistance(row['geom_path_ln3d_%s' % projstr], dim='2D')
        # compute xyLineh segment lengths and cumulative length
        distP2 = gT.computeAlongLineDistance(line2, dim='2D')
        # append to list for each event (row) in DF
        distancePath.append(distP)
        distanceEvent.append(distP2)

    # append to DF
    dbData['%s_PathDist' % name] = distancePath
    dbData['%s_LineDist' % name] = distanceEvent

    return dbData
