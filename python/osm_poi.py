# DETERMINE WHETHER TO RUN THIS SCRIPT ##############
import yaml

# load menu
with open("mnt/01-user-input/menu.yml", 'r') as f:
    menu = yaml.safe_load(f)

if menu['osm_poi']:
    print('run osm_poi')
    
    from os.path import exists
    import os
    import geopandas as gpd
    from pathlib import Path

    # SET UP #########################################
    # load city inputs files, to be updated for each city scan
    with open("mnt/01-user-input/city_inputs.yml", 'r') as f:
        city_inputs = yaml.safe_load(f)

    city_name_l = city_inputs['city_name'].replace(' ', '_').lower()

    # load global inputs, such as data sources that generally remain the same across scans
    with open("python/global_inputs.yml", 'r') as f:
        global_inputs = yaml.safe_load(f)

    # import GOSTnets -----------
    from GOSTnets.fetch_pois import OsmObject

    # Read AOI shapefile --------
    # transform the input shp to correct prj (epsg 4326)
    aoi_orig = gpd.read_file(f'mnt/city-directories/{city_name_l}/01-user-input/AOI/{city_name_l}.shp').to_crs(epsg = 4326)
    # buffer AOI by 5% of its width to capture roads immedately outside of city boundaries
    # TODO: determine whether to put this 5% buffer distance in one of the yaml files
    buff_dist = (aoi_orig.total_bounds[2] - aoi_orig.total_bounds[0]) * 0.05
    aoi_file = aoi_orig.buffer(buff_dist)
    features = aoi_file.geometry
    
    # Define output folder ---------
    output_folder = Path(f'mnt/city-directories/{city_name_l}/02-process-output/spatial')
    os.makedirs(output_folder, exist_ok=True)


    # EXTRACT OSM POI ##############################
    queries = {}
    if ('osm_query' in city_inputs) and bool(city_inputs['osm_query']):
        for tags in city_inputs['osm_query'].items():
            if not exists(output_folder / f'{city_name_l}_osm_{tags[0]}' / f'{city_name_l}_osm_{tags[0]}.shp'):
                # create the OsmObject
                queries[tags[0]] = OsmObject(f'{tags[0]}', features[0], tags[1])
    
    if bool(global_inputs['osm_query']):
        for tags in global_inputs['osm_query'].items():
            if not tags[0] in queries:
                if not exists(output_folder / f'{city_name_l}_osm_{tags[0]}.gpkg'):
                    # create the OsmObject
                    queries[tags[0]] = OsmObject(f'{tags[0]}', features[0], tags[1])
    
    for query in queries.items():
        try:
            result = query[1].GenerateOSMPOIs()
        
            # if query is not empty
            if result.empty == False:
                # try:
                query[1].RemoveDupes(0.0005)
                
                if 'name' in query[1].df.columns:
                    query_results = query[1].df[['amenity','geometry','name']]
                else:
                    query_results = query[1].df[['amenity','geometry']]

                # convert to GeoDataFrame
                query_results_gpd = gpd.GeoDataFrame(query_results, crs = "epsg:4326", geometry = 'geometry')
                query_results_gpd_shp = f'{city_name_l}_osm_{query[0]}'
                query_results_gpd.to_file(output_folder / f'{query_results_gpd_shp}.gpkg', driver='GPKG')
        except:
            pass
