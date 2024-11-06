# DETERMINE WHETHER TO RUN THIS SCRIPT ##############
import yaml

# load menu
with open("mnt/01-user-input/menu.yml", 'r') as f:
    menu = yaml.safe_load(f)

if menu['elevation']:
    print('run gee_elevation')
    
    import ee
    import geopandas as gpd

    # SET UP #########################################
    # load city inputs files, to be updated for each city scan
    with open("mnt/01-user-input/city_inputs.yml", 'r') as f:
        city_inputs = yaml.safe_load(f)

    city_name_l = city_inputs['city_name'].replace(' ', '_').replace("'", '').lower()

    # load global inputs
    with open("python/global_inputs.yml", 'r') as f:
        global_inputs = yaml.safe_load(f)

    # Initialize Earth Engine
    ee.Initialize()

    elevation = ee.Image("USGS/SRTMGL1_003")

    # Read AOI shapefile --------
    aoi_file = gpd.read_file(f'mnt/city-directories/{city_name_l}/01-user-input/AOI/{city_name_l}.shp').to_crs(epsg = 4326)

    # Convert shapefile to ee.Geometry ------------
    jsonDict = eval(gpd.GeoSeries([aoi_file['geometry'].force_2d().union_all()]).to_json())

    if len(jsonDict['features']) > 1:
        print('Need to convert polygons into a multipolygon')
        print('or do something else, like creating individual raster for each polygon and then merge')
        exit()
    
    AOI = ee.Geometry.MultiPolygon(jsonDict['features'][0]['geometry']['coordinates'])


    # PROCESSING #####################################
    no_data_val = -9999
    elevation_clip = elevation.clip(AOI).unmask(value = no_data_val, sameFootprint = False)

    # Export results to Google Cloud Storage bucket ------------------
    task0 = ee.batch.Export.image.toDrive(**{'image': elevation_clip,
                                             'description': f'{city_name_l}_elevation',
                                             'region': AOI,
                                             'scale': 30,
                                             'folder': global_inputs['drive_folder'],
                                             'maxPixels': 1e9,
                                             'fileFormat': 'GeoTIFF',
                                             'formatOptions': {
                                                 'cloudOptimized': True,
                                                 'noData': no_data_val
                                             }})
    task0.start()
