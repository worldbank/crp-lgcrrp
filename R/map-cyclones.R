# Mapping projected max speeds

p <- plot_layer(
  fuzzy_read(spatial_dir, layer_params$cyclones$fuzzy_string), "cyclones", plot_aoi = T) + 
  coord_3857_bounds(expansion = 20)
p$layers <- discard(p$layers, \(x) inherits(x$geom, "GeomMapTile"))

plots$cyclones <- p