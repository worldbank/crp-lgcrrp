# Water Salinity

# Revise original shapefile by erasing overlaps (keep highest salinity level)
# salinity <- vect("mnt/source-data/water-salinity/Salinity.shp")
# salinity_levels <- c(100, 1:6)
# salinity_no_overlap <- lapply(1:7, \(x) {
#   if (x == 7) return(filter(salinity, Numeric_va == salinity_levels[x]))
#   erase(filter(salinity, Numeric_va == salinity_levels[x]),
#         filter(salinity, Numeric_va %in% tail(salinity_levels, -x)))
# }) %>% bind_spat_rows()
# writeVector(salinity_no_overlap, "mnt/source-data/water-salinity/salinity-no-overlap.gpkg")

salinity_data <- vect("mnt/source-data/water-salinity/salinity-no-overlap.gpkg")

plot_water_salinity_regional <- function() {
  p <- plot_layer(salinity_data,
                  yaml_key = "water_salinity", plot_aoi = T) +
    coord_3857_bounds(expansion = 20)
  p$layers[detect_index(p$layers, \(x) inherits(x$geom, "GeomMapTile"))] <-
    annotation_map_tile(type = "cartolight", zoom = 9, progress = "none")[1]
  return(p)
}
plots$water_salinity <- plot_water_salinity_regional()

# National map
plot_water_salinity_national <- function() {
  p <- plot_layer(salinity_data,
                  yaml_key = "water_salinity", plot_aoi = F)
  p$layers[detect_index(p$layers, \(x) inherits(x$geom, "GeomMapTile"))] <-
    annotation_map_tile(type = "cartolight", zoom = 7, progress = "none")[1]
  bgd_3857_bbox <- st_bbox(
    aspect_buffer(project(salinity_data, "epsg:3857"),
                  aspect_ratio = aspect_ratio, buffer = 0.1))
  city_center <- centroids(aoi[which.max(expanse(aoi))]) %>%
    project("epsg:3857") %>%
    mutate(x = geom(.)[,"x"], y = geom(.)[,"y"])
  p +
    geom_spatvector(data = city_center, color = "black", shape = 1, size = 2) +
    geom_spatial_text_repel(
      data = city_center, aes(x = x, y = y, label = city),
      crs = "epsg:3857", direction = "x", vjust = "center") +
    coord_sf(
      crs = "epsg:3857",
      expand = F,
      xlim = bgd_3857_bbox[c(1,3)],
      ylim = bgd_3857_bbox[c(2,4)])
}
plots$water_salinity_national <- plot_water_salinity_national()
