# Plotting solar availability seasonality line chart

# If AOI contains multiple geometries, use the largest
aoi_largest <- project(aoi[which.max(expanse(aoi)),,], "epsg:4326")

setGDALconfig("GS_NO_SIGN_REQUEST=YES")
pvout_url <- "/vsigs/city-scan-global-data/globalsolar/PVOUT-monthly.tif"

monthly_pv <- rast(pvout_url) %>%
  terra::extract(aoi_largest, include_area = T) %>%
  .[,-1] %>% as.matrix() %>%
  { data.frame(
    month = 1:12,
    max = matrixStats::colMaxs(.),
    min = matrixStats::colMins(.),
    mean = colMeans(.) )}

pv_plot <- monthly_pv %>%
  ggplot(aes(x = month, y = mean)) +
  annotate("text", x = 1, y = 4.6, label = "Excellent Conditions", vjust = 0, hjust = 0, color = "dark grey") +
  annotate("text", x = 1, y = 3.6, label = "Favorable Conditions", vjust = 0, hjust = 0, color = "dark grey") +
  geom_line() +
  geom_point() +
  scale_x_continuous(breaks = 1:12, labels = lubridate::month(1:12, label = T) %>% as.character) +
  scale_y_continuous(labels = scales::label_comma(), limits = c(0, NA), expand = expansion(mult = c(0,.05))) +
  labs(title = "Seasonal availability of solar energy",
       x = "Month", y = "Daily PV energy yield (kWh/kWp") +
  geom_hline(yintercept = c(3.5, 4.5), linetype = "dotted") +
  theme_minimal() +
  theme(
    axis.title.x = element_blank(), 
    axis.line = element_line(linewidth = .5, color = "black"),
    panel.grid.minor.x = element_blank(),
    plot.background = element_rect(color = NA, fill = "white"))
ggsave(file.path(charts_dir, "monthly-pv.png"), plot = pv_plot, device = "png",
       width = 6, height = 4, units = "in", dpi = "print")
