# DETERMINE WHETHER TO RUN THIS SCRIPT ##############
import yaml

# load menu
with open("mnt/01-user-input/menu.yml", 'r') as f:
    menu = yaml.safe_load(f)

if menu['cyclone']:
    print('run cyclone')
    import os
    from pathlib import Path
    from shutil import copyfile

    # SET UP #########################################
    # load city inputs files, to be updated for each city scan
    with open("mnt/01-user-input/city_inputs.yml", 'r') as f:
        city_inputs = yaml.safe_load(f)

    city_name_l = city_inputs['city_name'].replace(' ', '_').replace("'", '').lower()

    # load global inputs, such as data sources that generally remain the same across scans
    with open("python/global_inputs.yml", 'r') as f:
        global_inputs = yaml.safe_load(f)

    # Define output folder ---------
    output_folder_parent = Path(f'mnt/city-directories/{city_name_l}/02-process-output')
    output_folder = output_folder_parent / 'spatial'
    os.makedirs(output_folder, exist_ok=True)


    # COPY DATA #####################################
    cyclone_data = 'mnt/source-data/cyclone/STORM_FIXED_RETURN_PERIODS_NI_50_YR_RP_BGD.tif'
    if os.path.exists(cyclone_data):
        copyfile(cyclone_data, f'{output_folder}/STORM_FIXED_RETURN_PERIODS_NI_50_YR_RP_BGD.tif')
    