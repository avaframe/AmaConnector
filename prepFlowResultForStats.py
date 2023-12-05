# -*- coding: utf-8 -*-
"""
Created on Thu Nov 30 12:53:43 2023

@author: LawineNaturgefahren
"""


import numpy as np
import geopandas as gpd
from shapely.ops import cascaded_union
from shapely.geometry import Point
from shapely.geometry import Polygon
from shapely.geometry import shape
from rasterio.features import shapes
import rasterio

'''
from shapely.geometry import LineString
import pathlib
import configparser
import amaConnector
import grab_demo as gD
import amaUtilities as aU
import shapely
import fiona
from rasterio.transform import Affine
from shapely.wkt import loads
from shapely.wkb import loads as wkb_loads
from rasterio.features import geometry_mask
from shapely.ops import unary_union
import matplotlib.pyplot as plt
from avaframe.in3Utils import cfgUtils
from avaframe.in3Utils import logUtils
import avaframe.in3Utils.fileHandlerUtils as fU
import avaframe.in3Utils.geoTrans as gT
import avaframe.out3Plot.amaPlots as aP
'''

def extract_elevation(x,y):
    row, col = demRaster.index(x,y)
    elevation = demData[row,col]
    return elevation

def add_elevation(geometry):
    x,y = geometry.exterior.xy
    vertices = [(xi, yi, extract_elevation(xi, yi)) for xi, yi in zip(x, y) ]
    elePolygon = Polygon(vertices)
    return elePolygon

def find_lowest_elevation(geometry):
    x, y = geometry.exterior.xy
    verticesElevation = [(xi, yi, extract_elevation(xi, yi)) for xi, yi in zip(x, y)]
    lowestVertex = min(verticesElevation, key=lambda vertex: vertex[2])
    lowestElevation = Point(lowestVertex[0], lowestVertex[1], lowestVertex[2])
    return lowestElevation



dem = r'C:\Users\LawineNaturgefahren\MagdalenaTest\AvaFrame\avaframe\data\aoi1\Inputs\DEMaoi1.tif'
flux = r'C:\Users\LawineNaturgefahren\MagdalenaTest\AvaFrame\avaframe\data\aoi1\Outputs\com4FlowPy\res_20231128_103513\flux.tif'

#Open rasterfiles from flowpy Calculation and Dem used as input for calculation
with rasterio.open(flux) as fluxRaster:
    fluxData= fluxRaster.read(1).astype('float32')
    fluxData[fluxData == -9999] = np.nan
    transformFlux= fluxRaster.transform
    
with rasterio.open(dem) as demRaster:
    # Read the DEM data as a NumPy array
    demData = demRaster.read(1).astype('float32')
    demData[demData == -9999] = np.nan
    transformDem = demRaster.transform
    
    
#rasterStack = np.stack ((fluxData, demData), axis =-1)


#vectorizing the fluxlayer (or provided FlowPy result raster)polygonmizes each pixel wich is not nan
mask = fluxData !=0
polygons = list(shapes(fluxData, mask = mask, transform=transformFlux))
fluxPoly = gpd.GeoDataFrame(geometry=[shape(s) for s,v in polygons])

#dissolving the neighbouring pixels to polygons, first one multpolygon, then splitting into single polygons. 
#only pixels which are connected via a side are dissolved, cornering pixels stay seperat
#TODO resolve crs! even though assingning one, none is shown in qgis, has to be assigned manually there again
fluxPoly['buffer'] = fluxPoly['geometry'].buffer(0)
dissolvedGeom = cascaded_union(fluxPoly['buffer'])
dissolvedPoly = gpd.GeoDataFrame(geometry=[dissolvedGeom])
dissolvedPoly = dissolvedPoly.explode()
dissolvedPoly.crs = 'EPSG:31287'

#add eleveation to each vertex --> Polygons with Z-Coordinate
dissolvedPoly['elevation'] = dissolvedPoly['geometry'].apply(add_elevation)
#extrecting the runoutpoint based on the lowest elevation of the vertex
dissolvedPoly['minEle'] = dissolvedPoly['geometry'].apply(find_lowest_elevation)



#Optionally exporting the polygon or point
#dissolvedPoly['minEle'].to_file(r'C:\Users\LawineNaturgefahren\MagdalenaTest\AmaConnector\data\amaExports\testPoint.gpkg', driver='GPKG')

