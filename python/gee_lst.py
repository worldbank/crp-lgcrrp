# DETERMINE WHETHER TO RUN THIS SCRIPT ##############
import yaml

# load menu
with open("mnt/01-user-input/menu.yml", 'r') as f:
    menu = yaml.safe_load(f)

if menu['summer_lst']:
    print('run gee_lst')
    
    import os
    import ee
    import math
    import geopandas as gpd
    import xarray as xr
    import numpy as np
    from pathlib import Path
    from os.path import exists

    # SET UP #########################################
    # load city inputs files, to be updated for each city scan
    with open("mnt/01-user-input/city_inputs.yml", 'r') as f:
        city_inputs = yaml.safe_load(f)

    city_name_l = city_inputs['city_name'].replace(' ', '_').replace("'", '').lower()

    # load global inputs
    with open("python/global_inputs.yml", 'r') as f:
        global_inputs = yaml.safe_load(f)

    # set output folder
    output_folder = Path(f'mnt/{city_name_l}/02-process-output/tabular')
    os.makedirs(output_folder, exist_ok=True)

    # Initialize Earth Engine
    ee.Initialize()

    landsat = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")

    # Read AOI shapefile --------
    aoi_file = gpd.read_file(f'mnt/{city_name_l}/01-user-input/AOI/{city_name_l}.shp').to_crs(epsg = 4326)
    centroid = aoi_file.centroid

    # Convert shapefile to ee.Geometry ------------
    jsonDict = eval(gpd.GeoSeries([aoi_file['geometry'].force_2d().union_all()]).to_json())

    if len(jsonDict['features']) > 1:
        print('Need to convert polygons into a multipolygon')
        print('or do something else, like creating individual raster for each polygon and then merge')
        exit()
    
    AOI = ee.Geometry.MultiPolygon(jsonDict['features'][0]['geometry']['coordinates'])


    # GEE PARAMETERS ################################
    # Identify hottest months using CRU data ----------------------
    if not exists(output_folder / f'{city_name_l}_hottest_months.txt'):
        temp_dict = {}
        for i in range(math.floor(city_inputs['first_year'] / 10) * 10, math.ceil(city_inputs['last_year'] / 10) * 10, 10):
            if i >= 2020:
                continue
            nc = xr.open_dataset(f"mnt/source-data/{global_inputs['temperature_source']}/cru_ts4.06.{i+1}.{i+10}.tmp.dat.nc")

            for month in range(1, 13):
                temp_dict[month] = []
                for year in range(max(i, city_inputs['first_year']), min(i+11, city_inputs['last_year'])):
                    time = str(year) + '-' + str(month) + '-15'
                    val = nc.sel(lon = centroid.x[0], lat = centroid.y[0], time = time, method = 'nearest')['tmp'].to_dict()['data']
                    temp_dict[month].append(val)
                temp_dict[month] = np.nanmean(temp_dict[month])
        
        avg_temp_dict = {}
        for month in range(1, 13):
            avg_temp_dict[(month-1)%12+1] = np.nanmean([temp_dict[(month-1)%12+1], temp_dict[(month)%12+1], temp_dict[(month+1)%12+1]])

        first_hot_months = max(zip(avg_temp_dict.values(), avg_temp_dict.keys()))[1]
        hottest_months = [first_hot_months, (first_hot_months)%12+1, (first_hot_months+1)%12+1]
        
        # Write hottest months to text ---------------------------
        with open(output_folder / f'{city_name_l}_hottest_months.txt', 'w') as file:
            # Write each number to the file on a new line
            for number in hottest_months:
                file.write(f"{number}\n")
    
    else:
        hottest_months = []
        with open(output_folder / f'{city_name_l}_hottest_months.txt') as file:
            for line in file:
                # Convert each line to an integer and append to the list
                hottest_months.append(int(line.strip()))
    
    # Date filter -----------------
    def ee_filter_month(month):
        if 1 <= month <= 11:
            return [ee.Filter.date(f'{year}-{str(month).zfill(2)}-01', f'{year}-{month+1}-01') for year in range(city_inputs['first_year'], city_inputs['last_year'] + 1)]
        elif month == 12:
            return [ee.Filter.date(f'{year}-12-01', f'{year+1}-01-01') for year in range(city_inputs['first_year'], city_inputs['last_year'] + 1)]
        else:
            return
    
    range_list0 = ee_filter_month(hottest_months[0])
    range_list1 = ee_filter_month(hottest_months[1])
    range_list2 = ee_filter_month(hottest_months[2])

    rangefilter = ee.Filter.Or(range_list0 + range_list1 + range_list2)
    
    # Cloud mask function ----------------
    def maskL457sr(image):
        # Bit 0 - Fill
        # Bit 1 - Dilated Cloud
        # Bit 2 - Cirrus (high confidence)
        # Bit 3 - Cloud
        # Bit 4 - Cloud Shadow
        qaMask = image.select('QA_PIXEL').bitwiseAnd(int('11111', 2)).eq(0)
        saturationMask = image.select('QA_RADSAT').eq(0)
        # Apply the scaling factors to the appropriate bands.
        thermalBand = image.select('ST_B10').multiply(0.00341802).add(149.0)
        # Replace the original bands with the scaled ones and apply the masks.
        return image.addBands(thermalBand, None, True).updateMask(qaMask).updateMask(saturationMask)


    # PROCESSING ###############################
    no_data_val = -9999
    collectionSummer = landsat.filter(rangefilter).filterBounds(AOI).map(maskL457sr).select('ST_B10').mean().add(-273.15).clip(AOI).unmask(value = no_data_val, sameFootprint = False)
    task = ee.batch.Export.image.toDrive(**{
        'image': collectionSummer,
        'description': f"{city_name_l}_summer",
        'folder': global_inputs['drive_folder'],
        'region': AOI,
        'scale': 30,
        'maxPixels': 1e9,
        'fileFormat': 'GeoTIFF',
        'formatOptions': {
            'cloudOptimized': True,
            'noData': no_data_val
        }
    })
    task.start()
