import random
import matplotlib.pyplot as plt
from importlib.resources import files
import matplotlib.font_manager as fm


font_resource = files(__package__) / 'hand.ttf'

font_path = font_resource.name  # the location of the font file
my_font = fm.FontProperties(fname=font_path)

random_color = lambda: '#' + ''.join([random.choice('0123456789ABCDEF') for _ in range(6)])


def plot_stacked_bar(categories, series, labels=None, colors=None, title='Simple Stacked Bar Chart', x_label='Category', y_label='Value'):
    # series: list of lists, each inner list is a series for the categories
    with plt.xkcd():
        fig, ax = plt.subplots(figsize=(6, 4))
        bottoms = [0] * len(categories)

        if labels is None:
            labels = [f'Series {i + 1}' for i in range(len(series))]

        # Default colors if none provided (will cycle if more series)
        default_colors = ['#4C78A8', '#F58518', '#54A24B', '#E45756', '#72B7B2', '#000000']
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
        plt.show()


def example_chart():
    categories = ['A', 'B', 'C', 'D']
    plot_stacked_bar(
        categories,
        series=[[1, 2, 3, 4], [5, 6, 7, 8], [2, 2, 2, 2], [6, 6, 6, 6]],
        labels=['Series A', 'Series B', 'Series C', 'Series D'],
        title='Simple Stacked Bar Chart'
    )


if __name__ == '__main__':
    example_chart()