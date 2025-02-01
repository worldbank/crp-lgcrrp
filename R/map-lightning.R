# Lightning

# First includes data for parts of surrounding countries, second only includes Bangladesh
# lightning_data <- rast("mnt/source-data/lightning/lis_vhrfc_1998_2013_v01-bgd.tif")
lightning_data <- rast("mnt/source-data/lightning/lis_vhrfc_1998_2013_v01-bgd-masked.tif")

plot_lightning_regional <- function() {
  p <- plot_layer(
    lightning_data,
    yaml_key = "lightning", plot_aoi = T) + 
    coord_3857_bounds(expansion = 20)
  p$layers[detect_index(p$layers, \(x) inherits(x$geom, "GeomMapTile"))] <- 
    annotation_map_tile(type = "cartolight", zoom = 9, progress = "none")[1]
  return(p)
}
plots$lightning_regional <- plot_lightning_regional()

# National map
plot_lightning_national <- function() {
p <- plot_layer(
    lightning_data,
    yaml_key = "lightning", plot_aoi = F)
  p$layers[detect_index(p$layers, \(x) inherits(x$geom, "GeomMapTile"))] <- 
    annotation_map_tile(type = "cartolight", zoom = 7, progress = "none")[1]
  bgd_3857_bbox <- st_bbox(aspect_buffer(project(lightning_data, "epsg:3857"), aspect_ratio = aspect_ratio, buffer = 0.1))
  city_center <- centroids(aoi[which.max(expanse(aoi))]) %>%
    project("epsg:3857") %>%
    mutate(x = geom(.)[,"x"], y = geom(.)[,"y"])
  p +
    geom_spatvector(data = city_center, color = "black", shape = 1, size = 2) +
    geom_spatial_text_repel(data = city_center, aes(x = x, y = y, label = city),
    crs = "epsg:3857", direction = "x", vjust = "center") +
    coord_sf(
      crs = "epsg:3857",
      expand = F,
      xlim = bgd_3857_bbox[c(1,3)],
      ylim = bgd_3857_bbox[c(2,4)]
      )
}
plots$lightning_national <- plot_lightning_national()
