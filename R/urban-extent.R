# Plotting built-up area time series line chart
wsf <- fuzzy_read(tabular_dir, "wsf_stats", read_csv) %>%
  rename(Year = year, uba_km2 = "cumulative sq km")
uba_plot <- wsf %>%
  ggplot +
  geom_line(aes(x = Year, y = uba_km2)) +
  scale_x_continuous(
    breaks = seq(1985, 2020, 5),
    minor_breaks = seq(1985, 2021, 1)) + 
  scale_y_continuous(labels = scales::comma, limits = c(0, NA), expand = c(0, NA)) +
  theme_minimal() +
  labs(title = paste(city, "Urban Built-up Area, 1985-2015"),
        y = bquote('Urban built-up area,'~km^2)) +
  theme(axis.line = element_line(linewidth = .5, color = "black"),
    axis.title.x = element_blank(),
    plot.background = element_rect(color = NA, fill = "white"))
ggsave(file.path(charts_dir, "wsf-built-up-area-plot.png"), plot = uba_plot, device = "png",
        width = 6, height = 4, units = "in", dpi = "print")
