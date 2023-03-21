import os, amaConnector
import pickle
import os
import pickle
import math
import numpy as np
import shapely
from shapely import wkb, wkt
global amaConnect
def grabAllComplete(outdir = os.path.join(os.getcwd(),'avalanches'), accessfile=os.path.join(os.getcwd(),'access.txt')):
    #if no accessfile param is set, it will assume a csv-file (including header, seperator: ';') access.txt inside the outdir with the following parameters: host, port, database, username, password
    os.makedirs(outdir,exist_ok=True)
    if not os.path.isfile(accessfile):
        accessfile = os.path.join(outdir, 'access.txt')
    amaConnect=amaConnector.amaAccess(accessfile)
    # select all events that have a release point
    data_dump = amaConnect.query("select * from event_full")
    #where not st_isempty(geom_rel_event_pt)"
    return data_dump

def convert(wkt_text):  # converts wkt well known text into z, y, z points.
    p = shapely.wkt.loads(wkt_text)
    return p


outdir = os.getcwd()
accessfile = os.path.join(outdir, 'access.txt')
data_dump = grabAllComplete(outdir=outdir, accessfile=accessfile)

print(data_dump)
