from kivy_garden.graph import Graph, MeshLinePlot
from controllers import get_today_totals


def create_daily_chart():
    totals = get_today_totals()
    g = Graph(
        xlabel="Metric",
        ylabel="Value",
        x_ticks_major=1,
        y_ticks_major=10,
        y_grid=True,
        x_grid=True,
        xmin=0,
        xmax=3,
        ymin=0,
        size_hint=(1, 1),
    )
    plot = MeshLinePlot()
    plot.points = [
        (0, totals["sugar_g"]),
        (1, totals["water_cups"]),
        (2, totals["insulin_units"]),
    ]
    g.add_plot(plot)
    return g
