import os
from shutil import copyfile
import yaml

# Set the environment variable in your code
# os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = "C:/Users/Owner/OneDrive/Documents/Career/World Bank/CRP/other/google-cloud-city-scan-service-account-key.json"

# load city inputs files, to be updated for each city scan
with open("mnt/01-user-input/city_inputs.yml", 'r') as f:
    city_inputs = yaml.safe_load(f)
city_name_l = city_inputs['city_name'].replace(' ', '_').replace("'", '').lower()

# make city directory
os.makedirs(f'mnt/city-directories/{city_name_l}/01-user-input/AOI', exist_ok=True)
os.makedirs(f'mnt/city-directories/{city_name_l}/02-process-output', exist_ok=True)
os.makedirs(f'mnt/city-directories/{city_name_l}/03-render-output', exist_ok=True)

# copy AOI into city directory
shp_suf0 = ['shp', 'shx', 'dbf']
shp_suf1 = ['prj', 'sbn', 'sbx', 'fbn', 'fbx', 'ain', 'aih', 'ixs', 'mxs', 'atx', 'shp.xml', 'cpg', 'qix', 'idx', 'qmd']
for suf in shp_suf0:
    copyfile(f'mnt/01-user-input/AOI/{city_inputs["AOI_shp_name"]}.{suf}', f'mnt/city-directories/{city_name_l}/01-user-input/AOI/{city_name_l}.{suf}')
for suf in shp_suf1:
    orig_file = f'mnt/01-user-input/AOI/{city_inputs["AOI_shp_name"]}.{suf}'
    if os.path.exists(orig_file):
        copyfile(orig_file, f'mnt/city-directories/{city_name_l}/01-user-input/AOI/{city_name_l}.{suf}')

# copy city inputs into city directory
copyfile("mnt/01-user-input/city_inputs.yml", f'mnt/city-directories/{city_name_l}/01-user-input/city_inputs.yml')

script_list = ["burned_area.py",
               'fwi.py',
               "gee_forest.py",
               "gee_landcover.py",
               "gee_lst_winter.py",
               "gee_lst.py",
               "gee_ndmi.py",
               "gee_ndvi.py",
               "gee_nightlight.py",
               "landcover_burnability.py",
               "osm_poi.py",
               "raster_processing.py",
               "road_network.py",
               "rwi.py",
               "soil_salinity.py",
               "contour_elev_stats.py",
               'slope.py',
               'flood_stats.py'
               ]

for s in script_list:
    with open(f'python/{s}') as f:
        exec(f.read())
