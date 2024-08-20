from shapely import wkb, LineString, Point, length
from shapely.ops import split
import math
import numpy as np
import pandas as pd
import geopandas
import avaframe.in3Utils.geoTrans as gT


def replaceMaxpotsize(row):
    if row['maxpotsize'] == 0 or row['avalanche_size'] > row['maxpotsize']:
        return row['avalanche_size']
    else:
        return row['maxpotsize']


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

import matplotlib.pyplot as plt
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

        #Check if point 1 or 2 is nan
        if pd.notna(row[point1]) and pd.notna(row[point2]):
            
           # check if point1 is located right at the start of the line - so when splitting line no effect
            if len(line1.geoms) == 1 or line1.geoms[0].boundary.geoms[0] == row[point1]:
                line1 = line1.geoms[0]
                
            else:
                # if point1 is located further down the line take the part of the line from the point1 onwards
                line1 = line1.geoms[1]
            # the split this line segment using point2 and use first line segment
            # resulting line2 is the line segment between point1 and point2
            
            # check if linestart und point 2 identical and if the point2 is on the track and not before 
            # add nan to all columns if this is the case
            #print([line1.coords[0][1]], [row[point2].coords[0][1]])
            
            if line1.coords[0][0] == row[point2].coords[0][0] or not row[point2].intersects(line1):
            
                dbData.loc[index, '%s_Distance' %name] = np.nan
                dbData.loc[index, '%s_Line' %name] = np.nan
                dbData.loc[index, '%s_LineStart' %name] = np.nan
                dbData.loc[index, '%s_Angle' %name] = np.nan
                dbData.loc[index, '%s_LineAltDrop' %name] = np.nan
                distancePath.append(np.nan)
                distanceEvent.append(np.nan)
           
            # calculate the values for the columns if a line exists
            else:
                
                line2 = split(line1, row[point2]).geoms[0]
                dbData.loc[index, '%s_Distance' % name] = length(line2)#line2.coords[-1][0]
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
                
        else:
          dbData.loc[index, '%s_Distance' %name] = np.nan
          dbData.loc[index, '%s_Line' %name] = np.nan
          dbData.loc[index, '%s_LineStart' %name] = np.nan
          dbData.loc[index, '%s_Angle' %name] = np.nan
          dbData.loc[index, '%s_LineAltDrop' %name] = np.nan
          distancePath.append(np.nan)
          distanceEvent.append(np.nan)
            
    # append to DF
    #print(distancePath)
    dbData['%s_PathDist' % name] = distancePath
    dbData['%s_LineDist' % name] = distanceEvent

    return dbData


def findAngleInProfile(pointAngle, avaPath, profile, dsMin):

    anglePara, incline, tmpPara, dsPara = gT.prepareAngleProfile(pointAngle, profile, raiseWarning=False)

    try:
        indSplitPoint = gT.findAngleProfile(tmpPara, dsPara, dsMin)
        pointFound = {'x': avaPath['x'][indSplitPoint], 'y': avaPath['y'][indSplitPoint],
                      'z': avaPath['z'][indSplitPoint], 'zPara': profile['z'][indSplitPoint],
                      's': profile['s'][indSplitPoint]}
    except IndexError:
        noSplitPointFoundMessage = ('Automated split point generation failed as no point where slope is less than %s°'
                                    'was found, provide the split point manually.' % pointAngle)
        pointFound = ''
        #log.warning(noSplitPointFoundMessage)

    return  pointFound


def addGradientForPoint (db, pathName, pointList, distance=0.1):
    """ calculates slope angle 

        Parameters
        -----------
       db:
            dataframe with relevant informations
       pathName:
           str with column name of the thalweg
       pointList:
           List of str with column names of points to be analysed
           

        Returns
        --------
        db: dataframe with added slope angles
    """
    
    #for loop over point list, to calculate slope angles of all relevant points
    for attr in pointList:
        targetPointList = db[attr]
        db[attr+'_gradient'] = 0
        #for loop to calculate slope angle for all thalwegs 
        for index, row in db.iterrows():
            
           
            path = db[pathName][index]
            targetPoint = targetPointList[index]
            if type(targetPoint) == type(Point()):
                
                #identification of the ID of the point of interest
                targetPoint = {'x':[targetPoint.x], 'y':[targetPoint.y]}
                targetPointID = gT.findClosestPoint(path.xy[0],path.xy[1], targetPoint)
                
                #determine if point is the first point of line (origin)
                if path.coords[targetPointID] == path.coords[0]:
                    pointBefore = Point(path.coords[targetPointID])
                    pointBehind = Point(path.coords[targetPointID + 1])
                
                    #determine if point is the last one (runout)
                if path.coords[targetPointID] == path.coords[-1]:
                    pointBefore = Point(path.coords[targetPointID])
                    pointBehind = Point(path.coords[targetPointID - 1])
                    
                if 'orig' in attr:
                    pointBefore = Point(path.coords[targetPointID])
                    pointBehind = Point(path.coords[targetPointID +2])
                    
                #'normal' slope angle calculation with 3 points ahead and 3 points after
                else: 
                   try:
                        pointBefore = Point(path.coords[targetPointID-3])
                        pointBehind = Point(path.coords[targetPointID+3])
                   except:
                       try:
                          pointBefore = Point(path.coords[targetPointID-2])
                          pointBehind = Point(path.coords[targetPointID+2])
                       except:
                          pointBefore = Point(path.coords[targetPointID-2])
                          pointBehind = Point(path.coords[targetPointID])
               
                # using determined points for input in gradient calcualtion
                slope = calculateSlope(pointBefore, pointBehind)
                
                db.loc[index, '%s_gradient' % attr] =abs(slope)
                #db[attr+'_gradient'][index] = slope
            
    return db

def calculateSlope(point1, point2):
    deltaEle = point1.z - point2.z
    dist = Point(point1).distance(Point(point2))
    slope = np.rad2deg(np.arctan(deltaEle / dist))
    return slope

'''
def decToDegrees(value):
    
    rad = math.atan(value)
    deg = math.degrees(rad)
    
    return deg
'''

def calcQuantiles (dbData, colList, qu = [0.25,0.5,0.75]):
    """ calculates statistical values to be exported as table

        Parameters
        -----------
       dbData:
            Dataframe with the relevant data
       colList:
           columns to be analysed
       qu:
           which quantiles should be calculated
           

        Returns
        --------
        quantilesTB: Dataframe with calculated statistics
    """
    quantileTB = pd.DataFrame(columns=['name','all','2','3','4','5'])
    #colList =['path_id', 'event_id']
    for col in colList:
        
        quantileM0 = dbData.groupby('maxpotsize')[col].quantile(qu[0])
        quantileM1 = dbData.groupby('maxpotsize')[col].quantile(qu[1])
        quantileM2 = dbData.groupby('maxpotsize')[col].quantile(qu[2])
        #quantileAll0 = dbData[col].quantile( qu[0])
        #quantileAll1 = dbData[col].quantile( qu[1])
        #quantileAll2 = dbData[col].quantile( qu[2])
        
        quantileAll0 = np.quantile(pd.Series(dbData[col]), qu[0])
        quantileAll1 = np.quantile(pd.Series(dbData[col]), qu[1])
        quantileAll2 = np.quantile(pd.Series(dbData[col]), qu[2])
        quantileAll0 = pd.Series(quantileAll0)
        quantileAll1 = pd.Series(quantileAll1)
        quantileAll2 = pd.Series(quantileAll2)
        
    
        index = quantileM0.index
        
        row = {'name': str(col)+'_'+str(qu[0]), 'all': round(quantileAll0,2)}
        for idx in index:
            row[str(idx)]=round(quantileM0[2],2)
            
        row = {'name': str(col)+'_'+str(qu[0]), 'all': round(quantileAll0[0],2), '2': round(quantileM0[2],2), '3': round(quantileM0[3],2), '4': round(quantileM0[4],2), '5': round(quantileM0[5],2)}
        
        row_df = pd.DataFrame([row])
        quantileTB = pd.concat([quantileTB, row_df], ignore_index=True)

        row = {'name': str(col)+'_'+str(qu[1]), 'all': round(quantileAll1,2)}
        for idx in index:
            row[str(idx)]=round(quantileM1[2],2)

        row = {'name': str(col)+'_'+str(qu[1]), 'all': round(quantileAll1[0],2), '2': round(quantileM1[2],2), '3': round(quantileM1[3],2), '4': round(quantileM1[4],2), '5': round(quantileM1[5],2)}
        row_df = pd.DataFrame([row])
        quantileTB = pd.concat([quantileTB, row_df], ignore_index=True)
    
        row = {'name': str(col)+'_'+str(qu[2]), 'all': round(quantileAll2,2)}
        for idx in index:
            row[str(idx)]=round(quantileM2[2],2)
            
        row = {'name': str(col)+'_'+str(qu[2]), 'all': round(quantileAll2[0],2), '2': round(quantileM2[2],2), '3': round(quantileM2[3],2), '4': round(quantileM2[4],2), '5': round(quantileM2[5],2)}
        row_df = pd.DataFrame([row])
        quantileTB = pd.concat([quantileTB, row_df], ignore_index=True)
        
    
    return quantileTB
                              
def addAngleDistXYOnFit(dbData, pathname, snappoints, fittedProfil, fitname=''):
    """ compute the slope, length, altitude diff, angle and snap on fit for fitted thalweg

    """

    for index, row in dbData.iterrows(): 
        
                
        path = row[pathname]
        origin = int(row['origin'] )
        
        
        for snappoint in snappoints:
            
            pointname1 = snappoint.find('_')
            pointname2 = snappoint.find('_', pointname1 + 1)
            pointname = snappoint[pointname1 + 1:pointname2]
            try:
                spoint = row[snappoint]
                spoint = {'x':[spoint.x], 'y':[spoint.y]}
                pointId = gT.findClosestPoint(path.xy[0],path.xy[1], spoint)
                snapOnFit = Point(row[fittedProfil].coords[pointId])
                
                line1 = split(row[fittedProfil], snapOnFit)
                length = line1.geoms[0].coords[-1][0]
                distanceFit = row[fittedProfil].xy[0][pointId]
                
                
                elevationDiff = Point(row[fittedProfil].coords[origin]).y - snapOnFit.y
                angle = np.rad2deg(np.arctan(elevationDiff / distanceFit))
                
                #db, slope = addGradientForPoint(dbData, pathname, [snappoint])
                pointbefore = Point(row[fittedProfil].coords[pointId-3])
                pointbehind = Point(row[fittedProfil].coords[pointId+3])
                dz = pointbefore.y - pointbehind.y
                ds = pointbehind.x - pointbefore.x
                slope = np.rad2deg(np.arctan(dz / ds))
                dbData.loc[index, '%s_slope_%s' %(pointname, fitname)] = abs(slope)
                dbData.loc[index, 'origin-%s_distance_%s' %(pointname,fitname)] = length
                dbData.loc[index, 'origin-%s_altDrop_%s' %(pointname,fitname)] = elevationDiff
                dbData.loc[index, 'origin-%s_angle_%s' %(pointname,fitname)] = angle
                dbData.loc[index, '%s_on_%s' %(pointname, fitname)] = snapOnFit
            except:
                continue
            
    return dbData

def calculatetravelLine(m, avaPath, origin):
    """ calculates line based on travel angle

        Parameters
        -----------
       m:
            gradient of line
       avaPath:
           dict with s,z coordinated of thalweg to determine length and points along the line
       origin:
           point of starting point as id
           

        Returns
        --------
        travelLine: Linestring with the coordinates of the travel line
    """
    
    
    intercept = avaPath['z'][origin] - m *avaPath['s'][origin]
    zValues = m*avaPath['s']+intercept 
    
    travelLine = LineString(list(zip(avaPath['s'][origin:], zValues[origin:])))
    
    return travelLine


def createCutOff (line, intersection):
    """ creates cut off between the thalweg line and the maximum travel angle, intersection between two lines

        Parameters
        -----------
       line:
            travel angle line, Linestring (result from calculatetravelLine)
       intersection:
           thalweg to be intersected, Linestring

        Returns
        --------
        endPointID: as ID for the point of intersection
    """
    maxX=None
    furthestIntersec = None
    for point in intersection.geoms:
        xCoord = point.x
        
        if maxX is None or xCoord > maxX:
            maxX = xCoord
            furthestIntersec = point
    
    x_values = [point[0] for point in line.coords]
    #y_values = [point[1] for point in d6Line.coords]
    endPointID = (np.abs(x_values - furthestIntersec.x)).argmin()
    #Origin hinterm Grad, gerade schneidet zweimal aber irrelevant
    return endPointID
