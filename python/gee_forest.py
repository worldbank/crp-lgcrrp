# DETERMINE WHETHER TO RUN THIS SCRIPT ##############
import yaml

# load menu
with open("mnt/01-user-input/menu.yml", 'r') as f:
    menu = yaml.safe_load(f)

if menu['forest']:
    print('run gee_forest')
    
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

    fc = ee.Image("UMD/hansen/global_forest_change_2023_v1_11")

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
    no_data_val = 0

    deforestation0023 = fc.select('loss').eq(1).clip(AOI).unmask(value = no_data_val, sameFootprint = False).rename('fcloss0023')
    forestCover00 = fc.select('treecover2000').gte(20).clip(AOI)
    # note: forest gain is only updated until 2012
    forestCoverGain0012 = fc.select('gain').eq(1).clip(AOI)
    forestCover23 = forestCover00.subtract(deforestation0023).add(forestCoverGain0012).gte(1).rename('fc23').unmask(value = no_data_val, sameFootprint = False)
    deforestation_year = fc.select('lossyear').clip(AOI).unmask(value = no_data_val, sameFootprint = False)

    # Export results to Google Cloud Storage bucket ------------------
    task0 = ee.batch.Export.image.toDrive(**{'image': forestCover23,
                                             'description': f'{city_name_l}_forest_cover23',
                                             'region': AOI,
                                            #  'scale': 30,
                                             'folder': global_inputs['drive_folder'],
                                             'maxPixels': 1e9,
                                             'fileFormat': 'GeoTIFF',
                                             'formatOptions': {
                                                 'cloudOptimized': True,
                                                 'noData': no_data_val
                                             }})
    task0.start()

    task1 = ee.batch.Export.image.toDrive(**{'image': deforestation_year,
                                             'description': f'{city_name_l}_deforestation',
                                             'region': AOI,
                                            #  'scale': 30,
                                             'folder': global_inputs['drive_folder'],
                                             'maxPixels': 1e9,
                                             'fileFormat': 'GeoTIFF',
                                             'formatOptions': {
                                                 'cloudOptimized': True,
                                                 'noData': no_data_val
                                             }})
    task1.start()
