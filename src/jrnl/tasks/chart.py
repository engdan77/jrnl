import random
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
from importlib.resources import files
import matplotlib.font_manager as fm
from matplotlib import patheffects

matplotlib.set_loglevel("critical")

font_resource: Path = files(__package__) / 'hand.ttf'
font_path = font_resource.as_posix()
my_font = fm.FontProperties(fname=font_path)

random.seed(42)  # Get more concistent colors
random_color = lambda: '#' + ''.join([random.choice('0123456789ABCDEF') for _ in range(6)])


def plot_stacked_bar(categories,
                     series,
                     labels=None,
                     colors=None,
                     title='Simple Stacked Bar Chart',
                     x_label='Category',
                     y_label='Value',
                     dark_mode=False,
                     display=False,
                     input_fig=None):
    # series: list of lists, each inner list is a series for the categories
    with plt.xkcd():
        if dark_mode:
            plt.style.use(['dark_background'])
            plt.rcParams['path.effects'] = [patheffects.withStroke(linewidth=0)]
            plt.rcParams['figure.facecolor'] = 'black'
        fig, ax = plt.subplots(figsize=(6, 4))
        if input_fig:
            fig = input_fig
            ax = fig.gca()
        bottoms = [0] * len(categories)

        if labels is None:
            labels = [f'Series {i + 1}' for i in range(len(series))]

        # Default colors if none provided (will cycle if more series)
        default_colors = [random_color() for _ in range(len(series))] + []
        if colors is None:
            colors = default_colors

        for i, s in enumerate(series):
            ax.bar(
                categories,
                s,
                bottom=bottoms,
                label=labels[i] if i < len(labels) else f'Series {i + 1}',
                color=colors[i % len(colors)]
            )
            bottoms = [b + v for b, v in zip(bottoms, s)]

        ax.set_title(title, fontproperties=my_font)
        ax.set_xlabel(x_label, fontproperties=my_font)
        ax.set_ylabel(y_label, fontproperties=my_font)
        for label in ax.get_xticklabels():
            label.set_fontproperties(my_font)
        for label in ax.get_yticklabels():
            label.set_fontproperties(my_font)
        ax.legend(prop=my_font)
        plt.tight_layout()
        if display:
            plt.show()


def plot_pie(
    labels,
    values,
    colors=None,
    title="Simple Pie Chart",
    autopct="%1.1f%%",
    startangle=90,
    explode=None,
    donut=False,
    legend=True,
    input_fig=None,
    dark_mode=False,
    display=False
):
    """
    Plot a pie (or donut) chart.

    labels: list[str] — labels for each wedge
    values: list[float] — sizes for each wedge
    colors: list[str] | None — custom colors; if None and random_color() exists, uses it
    autopct: str | None — format for percent labels; set None to hide
    startangle: float — starting rotation (degrees)
    explode: list[float] | None — explode distances per wedge, default 0.0s
    donut: bool — if True, draw a donut chart
    legend: bool — show legend
    """
    # Try to build default colors similar to your stacked bar helper
    if colors is None:
        try:
            # Use your existing helper if present
            colors = [random_color() for _ in range(len(values))]  # noqa: F821
        except NameError:
            colors = None  # fall back to matplotlib defaults

    if explode is None:
        explode = [0.0] * len(values)

    with plt.xkcd():
        if dark_mode:
            plt.style.use(['dark_background'])
            plt.rcParams['path.effects'] = [patheffects.withStroke(linewidth=0)]
            plt.rcParams['figure.facecolor'] = 'black'
        fig, ax = plt.subplots(figsize=(6, 4))
        if input_fig:
            fig = input_fig
        ax = fig.gca()

        wedges, texts, autotexts = ax.pie(
            values,
            labels=None,               # We'll use legend for labels (more space-efficient)
            colors=colors,
            autopct=autopct,
            startangle=startangle,
            explode=explode,
            wedgeprops=dict(width=0.4 if donut else 1.0, edgecolor="white"),
            pctdistance=0.75 if donut else 0.6,
            textprops=dict(color="black"),
        )

        # Title and font handling
        try:
            ax.set_title(title, fontproperties=my_font)  # noqa: F821
        except NameError:
            ax.set_title(title)

        # Apply custom font to pct texts if available
        try:
            for t in autotexts:
                t.set_fontproperties(my_font)  # noqa: F821
        except NameError:
            pass

        # For donut charts, optionally put a centered label or just keep it clean
        if donut:
            # You can add a center label like:
            # ax.text(0, 0, title, ha='center', va='center', fontproperties=my_font)
            pass

        if legend:
            try:
                ax.legend(
                    wedges,
                    labels,
                    loc="center left",
                    bbox_to_anchor=(1, 0.5),
                    prop=my_font,  # noqa: F821
                    title="",
                )
            except NameError:
                ax.legend(
                    wedges,
                    labels,
                    loc="center left",
                    bbox_to_anchor=(1, 0.5),
                    title="",
                )

        ax.set_aspect("equal")  # keep it circular
        plt.tight_layout()
        if display:
            plt.show()


def example_stacked_chart():
    categories = ['A', 'B', 'C', 'D']
    plot_stacked_bar(
        categories,
        series=[[1, 2, 3, 4], [5, 6, 7, 8], [2, 2, 2, 2], [6, 6, 6, 6]],
        labels=['Series A', 'Series B', 'Series C', 'Series D'],
        title='Simple Stacked Bar Chart'
    )


def example_pie_chart():
    labels = ['A', 'B', 'C', 'D']
    plot_pie(
        labels,
        values=[1, 2, 3, 4],
        title='Simple Pie Chart',
        display=True
    )


if __name__ == '__main__':
    example_pie_chart()