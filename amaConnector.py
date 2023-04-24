import psycopg2

import pandas.io.sql as sqlio
from shapely import wkt, wkb
import geopandas
import pandas
import warnings
warnings.filterwarnings('ignore') # setting ignore as a parameter

class amaAccess:
    access = []

    def __init__(self, inputfile, sep=':'):
        try:
            self.access = pandas.read_csv(inputfile,sep=sep)
        except:
            print("=========Error======")
            print("You most likely don't have the configuration file configured out.")
            print ("Please paste or create a configuration file into location '%s'"%(inputfile))
            print("This is a simple CSV (comma separated) textfile")
            print("make sure it uses the '%s' separator"%sep)
            print("and has the following column names in the first line -in fact, just copy&paste that and fill in the correct values in the second line, or ask the DB guy for a prepped file:")
            print()
            print('paste into %s and modify:'%inputfile)
            print('==================')
            print(sep.join(['host','db','port','user','password']))
            print(sep.join(['example.ama.host','example_ama_db','12345','your_username','super secret!!!']))
            print("==================")
    def insertQuery(self, schema, table, df):
        columns = ','.join('"'+df.columns+'"')

        server_ip = self.access['host'][0]
        db_name = self.access['db'][0]
        username = self.access['user'][0]
        pwd = self.access['password'][0]
        port = self.access['port'][0]
        # ...and connect please
        connstr = "host='{}' port={} dbname='{}' user={} password='{}'".format(server_ip, port, db_name, username,
                                                                               pwd)
        conn = psycopg2.connect(connstr
                                )

        cursor = conn.cursor()
        insert_req = []
        for index, data in df.iterrows():
            values=[]
            for col in data:
                s = str(col)
                if (s == 'None') or (s=='nan'):
                    s = 'NULL'
                if (type(col) == int or type(col)== float or s=='NULL' or s=='True' or s=='False'):
                    values.append(r'%s'%s)
                else:
                    values.append(r"'%s'" % s)
            strval = ','.join(values)
            insert_req.append("INSERT into %s.%s(%s) values(%s) ON CONFLICT DO NOTHING" % (schema, table, columns, strval))

        try:
            for el in insert_req:
                print(el)
                cursor.execute(el)
            conn.commit()
        except (Exception, psycopg2.DatabaseError) as error:
            print("Error: %s" % error)
            conn.rollback()
            cursor.close()
            return 1
        cursor.close()


    def query(self,query_list='SELECT * FROM event_full', constraint=''):
        try:
            if (query_list.lower().find('from') != -1):
                # Set up our connection
                #access = getAccess(r'c:\temp\ama_out\access.txt')
                server_ip = self.access['host'][0]
                db_name = self.access['db'][0]
                username = self.access['user'][0]
                pwd = self.access['password'][0]
                port = self.access['port'][0]
                # ...and connect please
                connstr = "host='{}' port={} dbname='{}' user={} password='{}'".format(server_ip, port, db_name, username, pwd)
                conn = psycopg2.connect(connstr
                    )
                sql = '{} {};'.format(query_list.strip(), constraint.strip())

                dat = sqlio.read_sql_query(sql, conn)
                conn = None
                return dat

            else:
                print('Something wrong with the query. No "select" and/or "from" encountered.')
        except:
            print('Error: Connection error.')
            raise

access =[]

def getAccess(inputfile, sep=';'):
    access = pandas.read_csv(inputfile,sep=sep)
    return access



def query(query_list='SELECT * FROM event_full', constraint=''):
    try:
        if (query_list.lower().find('from') != -1):
            # Set up our connection
            #access = getAccess(r'c:\temp\ama_out\access.txt')
            server_ip = access['host'][0]
            db_name = access['db'][0]
            username = access['user'][0]
            pwd = access['password'][0]
            port = access['port'][0]
            # ...and connect please
            connstr = "host='{}' port={} dbname='{}' user={} password='{}'".format(server_ip, port, db_name, username, pwd)
            conn = psycopg2.connect(connstr
                )
            sql = '{} {};'.format(query_list.strip(), constraint.strip())


            dat = sqlio.read_sql_query(sql, conn)
            conn = None
            return dat

        else:
            print('Something wrong with the query. No "select" and/or "from" encountered.')
    except:
        print('Error: Connection error.')
        raise


# Connect to an existing database
def eventlist(constraint='', geom_only=False):
    if (geom_only):
        sql = 'SELECT * FROM event_geom'
    else:
        sql = 'SELECT * FROM event_full'
    dat = query(sql, constraint)
    # drop connection after use

    # use well-known-text geometry, create designated geometry column for geopandas
    dat['geom'] = dat['pt'].apply(wkt.loads)

    if dat is not None:
        geodat = geopandas.GeoDataFrame(dat, geometry='geom')
    return geodat

def eventlist(constraint='', geom_only=False):
    sql = 'SELECT * FROM event_full'
    dat = query(sql, constraint)
    # drop connection after use

    # use well-known-text geometry, create designated geometry column for geopandas
    dat['geom'] = dat['pt'].apply(wkt.loads)

    if dat is not None:
        geodat = geopandas.GeoDataFrame(dat, geometry='geom')
    return geodat

def designlist(constraint='', geom_only=False):

    sql = 'SELECT * FROM event_full2 where not (geom_rel_event_poly3d is  NULL)'
    dat = query(sql, constraint)
    # drop connection after use

    # use well-known-text geometry, create designated geometry column for geopandas
    dat['geom'] = dat['geom_rel_event_poly3d'].apply(wkb.loads, hex=True)

    if dat is not None:
        geodat = geopandas.GeoDataFrame(dat, geometry='geom')
    return geodat


# Connect to an existing database
def pathlist(constraint=''):

    sql = 'SELECT * FROM event_full2'
    dat = query(sql, constraint)
    # drop connection after use

    # use well-known-text geometry, create designated geometry column for geopandas
    dat['geom'] = dat['path_ln'].apply(wkb.loads,hex=True)

    if dat is not None:
        geodat = geopandas.GeoDataFrame(dat, geometry='geom')
        geodat.to_csv(filePath, sep=',', float_format='%.')
    return geodat


def event_minimum(constraint='', use3d=True):
    # will return only event point and path line geometries (either 3d oder 2d) from events as selected by the constraint list
    if (use3d):
        query_list = 'SELECT pt3d, path_ln3d FROM event_full'
        geom_col = 'pt3d'
    else:
        query_list = 'SELECT pt, path_ln FROM event_full'
        geom_col = 'pt'
    dat = query(query_list, constraint)

    dat['geom'] = dat[geom_col].apply(wkt.loads)
    if dat is not None:
        geodat = geopandas.GeoDataFrame(dat, geometry='geom')
    return geodat




