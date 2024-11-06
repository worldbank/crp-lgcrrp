# DETERMINE WHETHER TO RUN THIS SCRIPT ##############
import yaml

# load menu
with open("mnt/01-user-input/menu.yml", 'r') as f:
    menu = yaml.safe_load(f)

if menu['rwi']:
    print('run rwi')
    
    import os
    import pandas as pd
    import geopandas as gpd
    from pyquadkey2.quadkey import QuadKey
    from pyquadkey2.quadkey import TileAnchor, QuadKey
    from shapely.geometry import Polygon
    from pathlib import Path
    from os.path import exists

    # SET UP #########################################
    # load city inputs files, to be updated for each city scan
    with open("mnt/01-user-input/city_inputs.yml", 'r') as f:
        city_inputs = yaml.safe_load(f)

    city_name_l = city_inputs['city_name'].replace(' ', '_').replace("'", '').lower()

    # load global inputs, such as data sources that generally remain the same across scans
    with open("python/global_inputs.yml", 'r') as f:
        global_inputs = yaml.safe_load(f)

    # Read AOI shapefile --------
    # transform the input shp to correct prj (epsg 4326)
    aoi_file = gpd.read_file(f'mnt/city-directories/{city_name_l}/01-user-input/AOI/{city_name_l}.shp').to_crs(epsg = 4326)
    features = aoi_file.geometry

    # Define output folder ---------
    output_folder_parent = Path(f'mnt/city-directories/{city_name_l}/02-process-output')
    output_folder = output_folder_parent / 'spatial'
    os.makedirs(output_folder, exist_ok=True)

    # PROCESS RWI DATA ################################
    rwi_data = f"mnt/source-data/{global_inputs['rwi_source']}/{city_inputs['country_iso3']}_relative_wealth_index.csv"
    
    if exists(rwi_data):
        if not exists(output_folder / f"{city_name_l}_rwi.gpkg"):
            FB_QKdata = pd.read_csv(rwi_data)
            # change quadkey format to str
            FB_QKdata["quadkey1"] = FB_QKdata["quadkey"].astype('str')
            # fill 13 digit quadkeys with 0 before the QK
            FB_QKdata['quadkey1'] = FB_QKdata['quadkey1'].apply(lambda x: x.zfill(14))
            # take column with quadkeys and transform it to list and then to QuadKey object
            fb_qk = FB_QKdata["quadkey1"].tolist()
            FB_QK = [QuadKey(i) for i in fb_qk]

            # locate the four corners of QuadKey tiles
            SW = []
            NE = []
            SE = []
            NW = []

            for i in FB_QK:
                #south west point
                sw = i.to_geo(anchor=TileAnchor.ANCHOR_SW)
                SW.append(sw) 
                #north west point
                ne = i.to_geo(anchor=TileAnchor.ANCHOR_NE)
                NE.append(ne) 
                #south east point 
                se = i.to_geo(anchor=TileAnchor.ANCHOR_SE)
                SE.append(se)
                #north west point 
                nw = i.to_geo(anchor=TileAnchor.ANCHOR_NW)
                NW.append(nw)
            
            # flip lat and lon for tile corner coordinates
            swFinal = [(i[1], i[0]) for i in SW]
            neFinal = [(i[1], i[0]) for i in NE]
            seFinal = [(i[1], i[0]) for i in SE]
            nwFinal = [(i[1], i[0]) for i in NW]

            # generate Polygon object based on four corner coordinates
            tiledata = [Polygon([nw, sw, se, ne]) for sw, ne, se, nw in zip(swFinal, neFinal, seFinal, nwFinal)]

            # create GeoDataFrame with Polygons
            gdf = gpd.GeoDataFrame(geometry = tiledata, crs = "epsg:4326")

            # add QuadKeys to gdf
            gdf['quadkey'] = FB_QK

            # change type of quadkey column to str
            gdf["quadkey"] = gdf["quadkey"].astype('str')

            # merge gdf and fb data
            gdf = gdf.merge(FB_QKdata, left_on = 'quadkey', right_on = 'quadkey1', how = 'inner')

            # export to shapefile
            gdf_aoi = gpd.clip(gdf, aoi_file)

            gdf_aoi.set_crs(crs = 'epsg:4326').to_file(output_folder / f"{city_name_l}_rwi.gpkg")
    else:
        print(f'No RWI data for {city_inputs["country_iso3"]}')
