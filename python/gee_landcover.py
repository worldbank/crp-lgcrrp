# DETERMINE WHETHER TO RUN THIS SCRIPT ##############
import yaml

# load menu
with open("mnt/01-user-input/menu.yml", 'r') as f:
    menu = yaml.safe_load(f)

if menu['landcover']:
    print('run gee_landcover')
    
    import os
    import ee
    import geopandas as gpd
    import csv
    from pathlib import Path

    # SET UP #########################################
    # load city inputs files, to be updated for each city scan
    with open("mnt/01-user-input/city_inputs.yml", 'r') as f:
        city_inputs = yaml.safe_load(f)

    city_name_l = city_inputs['city_name'].replace(' ', '_').replace("'", '').lower()

    # load global inputs
    with open("python/global_inputs.yml", 'r') as f:
        global_inputs = yaml.safe_load(f)

    # set output folder
    output_folder = Path(f'mnt/city-directories/{city_name_l}/02-process-output/tabular')
    os.makedirs(output_folder, exist_ok=True)

    # Initialize Earth Engine
    ee.Initialize()

    lc = ee.ImageCollection('ESA/WorldCover/v200').first()

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
    lc_aoi = lc.clip(AOI)

    # Calculate stats -----------------------
    # Calculate the pixel counts for each land cover type
    lc_hist = lc_aoi.reduceRegion(
        reducer=ee.Reducer.frequencyHistogram(),
        geometry=AOI,
        scale=10,
        maxPixels=1e9
    )
    lc_hist1 = lc_hist.getInfo()['Map']
    
    # Create a dictionary to store the counts
    counts_dict = {}

    # Create value dictionary
    class_values = {
        10: 'Tree cover',
        20: 'Shrubland',
        30: 'Grassland',
        40: 'Cropland',
        50: 'Built-up',
        60: 'Bare / sparse vegetation',
        70: 'Snow and ice',
        80: 'Permanent water bodies',
        90: 'Herbaceous wetland',
        95: 'Mangroves',
        100: 'Moss and lichen'
    }

    # Populate the dictionary with counts for each land cover type
    for class_val in class_values:
        class_name = class_values[class_val]
        count = lc_hist1.get(str(class_val), 0)
        counts_dict[class_name] = count

    # Write the counts dictionary to a CSV file
    with open(output_folder / f'{city_name_l}_lc.csv', 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=['Land Cover Type', 'Pixel Count'])
        writer.writeheader()
        for class_name, count in counts_dict.items():
            writer.writerow({'Land Cover Type': class_name, 'Pixel Count': count})

    # Export results to Google Cloud Storage bucket ------------------
    no_data_val = -9999
    lc_aoi = lc_aoi.unmask(value = no_data_val, sameFootprint = False)
    task0 = ee.batch.Export.image.toDrive(**{'image': lc_aoi,
                                             'description': f'{city_name_l}_lc',
                                             'region': AOI,
                                            #  'scale': 10,
                                             'folder': global_inputs['drive_folder'],
                                             'maxPixels': 1e9,
                                             'fileFormat': 'GeoTIFF',
                                             'formatOptions': {
                                                 'cloudOptimized': True,
                                                 'noData': no_data_val
                                             }})
    task0.start()
