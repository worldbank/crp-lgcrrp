# README

This project collects and processes spatial data, and uses them to generate maps and charts to be used in local preparedness plans.

## To setup

First, clone this repository:

```
git clone --filter=tree:0 https://github.com/worldbank/crp-lgcrrp.git
```

Flood data is proprietary and therefore cannot be directly accessed by this public repository. To include flooding, please request flood data from bnotkin@worldbank.org. Once received, you will then place it in `mnt/source-data/` so that the resulting file path is `mnt/source-data/fathom/`.

## To run

This project has two phases: data collection & processing, and data visualization. The first phase is conducted by `01-main.py`, while `02-main.R` handles the second.

For data collection, you will need to
1. ensure city AOI (area of interest) is located in `mnt/01-user-input/AOI/`;
2. edit `mnt/01-user-input/city_inputs.yml` to name city and path to AOI;
3. edit `mnt/01-user-input/menu.yml` to only include the desired layers; and
4. run `01-main.py` with the command `python 01-main.py`

Once `01-main.py` has finished running, simply run `Rscript 02-main.R`

This process will result in a city-specific directory with spatial data files, maps, and charts.

```
- mnt/
	- city-directories/
		- <city name>/
			- 01-user-input/
			- 02-process-output/ (All of the intermediary files, mainly GeoTIFFs)
			- 03-render-output/
				- maps/
				- charts/
```

## Possible maps

To learn more about these map layers, see the project [wiki](https://github.com/worldbank/crp-lgcrrp/wiki).


1. Population
2. Relative wealth
3. Economic activity
4. Economic change
5. Urban extent
6. Land cover
7. Solar
8. Air quality
9. Land surface temperature (summer)
10. Vegetation index (annual and/or seasonal)
11. Forest cover & deforestation
12. Flooding (fluvial, pluvial, coastal, and combined)
13. Elevation
14. Slope
15. Landslide susceptibility
16. Liquefaction susceptibility
17. Roads
18. Moisture index (annual and/or seasonal)

## Possible charts

To learn more about these charts, see the project [wiki](https://github.com/worldbank/crp-lgcrrp/wiki).

1. Population growth
2. Urban extent over time
3. Urban extent's flooding exposure over time (fluvial, pluvial, coastal, and combined)
4. Land cover distribution
5. Elevation distribution
6. Slope distribution
7. Solar energy availability over year
8. Fire weather index over year
9. Cold spell duration index
10. Warm spell duration index
11. Hot days, tropical nights
12. Days with more than 20 & 50 mm of precipitation
13. Extreme 5-day precipitation
14. Projected temperatures
