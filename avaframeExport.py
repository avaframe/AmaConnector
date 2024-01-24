import amaConnector
import os
from os import path
import geopandas, pandas as pd
from osgeo import gdal
from shapely import wkb
from datetime import datetime
import csv
import numpy as np
def checkDir(dir):
    dir=dir.replace(' ','')
    if not os.path.isdir(dir):
        os.makedirs(dir, exist_ok=True)
    return dir

def checkPath(filePath):
    filePath = filePath.replace('/',path.sep).replace('\\',path.sep)
    #use system specific path separators
    dir = checkDir(path.dirname(filePath))
    #prepare directory if not yet exists
    outPath = path.join(dir, path.basename(filePath))
    if path.isfile(outPath):
        try:
            os.remove(outPath)
        except:
            print('cannot remove file, probably trying to overwrite a file we just created.')
            outPath=''

    return outPath
def grabRaster(config, outdir, design_event=False, projstr ='', constraint=''):
    if (design_event):
        schema = 'design' # Design refers to reference avalanches meant for designing mitigation measures etc.
    else:
        schema = 'public' # Public refers to actual, real-life avalanches
    if projstr == '':
        projstr = amaConnect.query("select * from getclosestconf('%s','projection_raster')"%config)['getclosestconf'][0]
    #getting the output projection config as stored in the config table

    epsg = int(projstr.lower().replace('epsg:','').strip())
    print('using output projection EPSG:%d'%epsg)
    buffersize = int(amaConnect.query("select * from getclosestconf('%s','raster_buffer')"%config)['getclosestconf'][0])
    print('using a buffer size of %d [coordinate system units]'%buffersize)
    outputformat = amaConnect.query("select * from getclosestconf('%s','raster_format')"%config)['getclosestconf'][0]
    #
    pathList = amaConnect.query('select distinct path_id, event_id from %s.event_full' % schema, constraint)
    for index, path in pathList.iterrows():
        path_id= path['path_id']
        event_id = path['event_id']
        #rasterquery = "with extent as (select st_swapordinates(st_buffer(st_transform(ln,%s),%d),'xy') as ext from paths where paths.path_id = %d) \
        #                            select st_astiff(st_union(st_clip(rast, ext))) as raster from dem right join extent on st_intersects(dem.rast, extent.ext) group by ext" % (
        #epsg, buffersize, path_id)
        rast = amaConnect.query("select * from st_astiff(getraster(%d,%d,%d))"%(path_id, epsg, buffersize))
        outfile = checkPath(amaConnect.query("select * from getstructure(%d,'raster_dem','%s')"%(event_id,config))['getstructure'][0].replace('%outdir%',outdir))
        if len(outfile)>0:
            print('saving tiff to %s'%outfile)
            with  open(outfile, 'wb') as savefile:
                savefile.write(rast['st_astiff'][0])
            if outputformat.lstrip(' .').lower() not in ['tif', 'tiff', 'geotiff']:
                print('DB configuration suggests using raster format "%s"'% outputformat)
                customOut = checkPath(outfile.replace('.tif', '.%s' % outputformat.lstrip(' .').lower()))
                print('Writing output file %s'%customOut)
                ds = gdal.Open(outfile)
                gdal.Translate(customOut, ds)
                ds = None
                if os.path.isfile(customOut):
                    print('file converted to selected output format, removing tiff %s'%outfile)
                    try:
                        os.remove(outfile)
                    except:
                        print('cannot remove file right now. you might have to live with a bit of additional hdd clutter for now, remove it yourself if you like')
        else:
            print('skipping.')
    return len(pathList)

def writeConfig(eng, configfile, configname):
    #reads CSV file from path <configfile>, expects columns ['key', 'value'], using DB engine <eng>
    #will enter the presented configuration value-pairs into DB table ext_project, using configuration <configname>
    df = pd.read_csv(configfile, quoting=csv.QUOTE_ALL)
    res = None
    cols =  df.columns.tolist()
    if 'key' in cols and 'value' in cols: #seems like the reading worked
        df['conf_group'] = configname
        df.rename({'key': 'conf_key', 'value': 'conf_textvalue'})
    if not 'conf_numvalue' in cols:
        df['conf_numvalue'] = np.nan
    df['cfg_id'] = 'default'
    if 'conf_key' in cols and 'conf_textvalue' in cols:
        df['conf_textvalue']=df['conf_textvalue'].astype(str)
        res = configEnter(eng,df, configname)

    return res

def configEnter(eng,df, configname):
    #upserts configuration values from dataframe to ext_project table
    qry = ''
    schema = 'public'
    table = 'ext_project'
    valrep = {"'default'":"default", 'nan': 'NULL', "'NULL'": "NULL"}
    for index, row in df.iterrows():
            colstr = amaConnector.listToPGstr(df.columns.tolist())
            valstr = amaConnector.listToPGstr(row.tolist(),r"'")
            for key in valrep.keys():
                valstr = valstr.replace(key, valrep[key])

            qry += "INSERT INTO %s.%s %s VALUES %s ON CONFLICT (""conf_group"", ""conf_key"", ""conf_numvalue"") DO UPDATE SET conf_textvalue = excluded.conf_textvalue;\n" %(schema, table, colstr, valstr)
    eng.insertquery(qry)
    return getconfig(eng, configname)


def getconfig(eng, configname):
    return eng.query("with abc as (select getconfparents('%s') as configs) select conf_group, conf_key, conf_textvalue, conf_numvalue from ext_project, abc where conf_group = any(abc.configs)"%(configname))

def saveConfig(eng, configfile, configname):
    #writes CSV file to path <configfile> with columns ['key', 'value'], using DB engine <eng>
    #will store the used configuration <configname> to disk for reference
    configs = getconfig(eng, configname)
    configs.to_csv(configfile, quoting=csv.QUOTE_ALL, index=False)
    return configs





def grabEvents(config, outpath,design_event=False, projstr = 'epsg:31287', constraint = '' ):
    if (design_event):
        schema = 'design' # Design refers to reference avalanches meant for designing mitigation measures etc.
    else:
        schema = 'public' # Public refers to actual, real-life avalanches
    if projstr == '':
        projstr = amaConnect.query("select * from getclosestconf('%s','projection_raster')" % config)['getclosestconf'][0]
    # getting the output projection config as stored in the config table

    epsg = int(projstr.lower().replace('epsg:', '').strip())
    print('using output projection EPSG:%d' % epsg)
    eventList = amaConnect.query('select distinct event_id from %s.event_full'%schema, constraint)
    #this retrieves the event_ids of all relevant events


    geometryCols = amaConnect.query("select * from getclosestconf('%s','exportgeometry')"%config)
    #geometryCols = {'getclosestconf': ['geom_event_pt, geom_path_ln, geom_event_ln, geom_rel_pt, geom_rel_ln']}
    #this asks the database for the stored geometry column names which should get exported in the current configuration

    for index, event in eventList.iterrows():
        event_id = event['event_id']
        print('exporting event_id %d'%event_id)
        for geomCol in geometryCols['getclosestconf'][0].split(','):
            col = geomCol.strip()
            print('collecting data for geometry column %s' % col)
            geometry = amaConnect.query("select * from %s.exporteventgeom(%d, '%s', '%s')"%(schema, event_id, col, config))
            #this retrieves the geometry in combination with an output path according to the current config - structure_geom_xyz


            if not (geometry['geom'].isnull()[0]): #only work with existing geometries
                geometry['geom'] = geometry['geom'].apply(wkb.loads, hex=True)

                attr = amaConnect.query("select * from %s.extractattributes(%d, '%s', '%s')" % (schema, event_id, col, config))
                #this retrieves the selected set of attributes according to the current configuration and the current geometry column
                # one may set different (or none at all) attributes to be included in paths, release lines etc.
                attributes = pd.DataFrame([attr['value']]).rename(columns=attr['key']).reset_index(drop=True)
                feature = geometry.join(attributes)
                geodf =  geopandas.GeoDataFrame(feature, geometry='geom').set_crs(projstr)

                outPath = geodf['struct'][0].replace('%outdir%',outpath)
                #filling in the last variable, %outdir%, in the output path
                outPath=checkPath(outPath)
                if len(outPath)>0:
                #this will prepare the subdirectory and change the output path if necessary; general aim is to get a valid, writeable path within an existing directory
                    print('using output path %s'%outPath)
                    geodf.to_file(outPath, driver='ESRI Shapefile')
                else:
                    print('skipping file')
            else:
                print('Geometry empty, skipping output!')
            #exportfile(dataOut, geometry['struct'], outpath)

    return len(eventList)


global amaConnect
#outdir = ''
outdir = r'c:\temp\my_export_dir'
#if you want to, uncomment and set your own export dir above -this should point to an already created directory.
#otherwise, the following function will create a valid, individual export directory based on the current time:
exportdate = datetime.now().strftime('export_%Y-%m-%d_%H-%M-%S')
if not os.path.isdir(outdir):
    outdir = path.join(os.path.dirname(os.getcwd()),exportdate)
    print('Using output directory %s'%outdir)
    os.makedirs(outdir, exist_ok=True)


#fill in configurations if necessary:
configuration = 'avaframe' # this refers to the configuration variables, as set in the DB table "ext_project" ("External Project configuration" in QGIS)
useDesignEvents = False #set to True if you want to export Design Events instead of real recorded Events
constraint = "WHERE event_id = 582" #this constraint delivers only Event 582 (Gaiskogel Nordwest)



accessFile = path.join(os.getcwd(),'fullaccess_ama.txt')
conffile = path.join(os.getcwd(), 'config.ini')
amaConnect = amaConnector.amaAccess(accessFile)

#writeConfig(amaConnect, conffile, 'tmpconf2' )




#

conf = saveConfig(amaConnect, conffile, configuration)
try:
    with open(path.join(outdir,'log.txt'),'w') as file:
        file.write('Time: %s\n'%exportdate)
        file.write('Exporting db using export configuration "%s"\n'%configuration)
        file.write('configuration saved to "%s"' % conffile)
        file.write('Design Events: %s\n' %useDesignEvents)
        file.write('Using constraint: "%s"\n'%constraint)

except:
    print ("ERROR --------- no writing access to directory '%s'!"%outdir)
#initAma(outpath, accessFile, ':')
projstr='' #possible override, use format 'epsg:4326'
eventsRes= grabEvents(configuration,outdir, useDesignEvents, projstr, constraint)
rasterRes= grabRaster(configuration,outdir, useDesignEvents,projstr, constraint)
try:
    with open(path.join(outdir,'log.txt'),'a') as file:
        file.write('====Results====\n')
        file.write('Written %d events"\n'%eventsRes)
        file.write('Written %d path rasters\n'%rasterRes)


except:
    print ("ERROR --------- no writing access to directory '%s'!"%outdir)
