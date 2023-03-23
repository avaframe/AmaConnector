import amaConnector
from shapely import wkb, wkt

def convert(wkt_text):
    """ converts wkt well known text into z, y, z points """

    # convert using shapely
    p = shapely.wkt.loads(wkt_text)

    return p
