# Mapping projected max speeds

p <- plot_layer(
  rast("mnt/source-data/cyclone/STORM_FIXED_RETURN_PERIODS_NI_50_YR_RP_BGD.tif"),
  yaml_key = "cyclones", plot_aoi = T) + 
  coord_3857_bounds(static_map_bounds, expansion = 20)
p$layers <- discard(p$layers, \(x) inherits(x$geom, "GeomMapTile"))

plots$cyclones <- p
