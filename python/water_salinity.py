# DETERMINE WHETHER TO RUN THIS SCRIPT ##############
import yaml

# load menu
with open("mnt/01-user-input/menu.yml", 'r') as f:
    menu = yaml.safe_load(f)

if menu['water_salinity']:
    print('run water salinity')

    import os
    import pandas as pd
    import geopandas as gpd
    from pathlib import Path
    from os.path import exists

    # SET UP #########################################
    # load city inputs files, to be updated for each city scan
    with open("mnt/01-user-input/city_inputs.yml", 'r') as f:
        city_inputs = yaml.safe_load(f)

    city_name_l = city_inputs['city_name'].replace(' ', '_').replace("'", '').lower()
    country_name_l = city_inputs['country_name'].replace(' ', '_').replace("'", '').lower()

    # load global inputs, such as data sources that generally remain the same across scans
    with open("python/global_inputs.yml", 'r') as f:
        global_inputs = yaml.safe_load(f)

    # Read AOI shapefile --------
    # transform the input shp to correct prj (epsg 4326)
    aoi_file = gpd.read_file(f'mnt/city-directories/{city_name_l}/01-user-input/AOI/{city_name_l}.shp').to_crs(epsg = 4326)

    # Define output folder ---------
    output_folder = Path('mnt/02-process-output')

    os.makedirs(output_folder, exist_ok=True)
    

    # SET PARAMETERS ################################
    water_bodies = ['Groundwaters', 'Lakes_Reservoirs', 'Rivers']
    data_types = ['database', 'summary']


    # PROCESS DATA ##################################
    # filter country data
    data_folder = Path('data')
    ws_folder = data_folder / 'water_salinity'

    os.makedirs(ws_folder, exist_ok=True)
    
    for water_body in water_bodies:
        for data_type in data_types:
            if not exists(ws_folder / f'{country_name_l}_{water_body}_{data_type}.csv'):
                df = pd.read_csv(Path(f"mnt/source-data/{global_inputs['water_salinity_source']}") / f'{water_body}_{data_type}.csv', low_memory = False)
                df[df['Country'] == city_inputs['country_name']].to_csv(ws_folder / f'{country_name_l}_{water_body}_{data_type}.csv')
    