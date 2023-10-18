import bokeh
import numpy as np
import pandas as pd

from pydatalab.blocks.base import DataBlock
from pydatalab.bokeh_plots import mytheme
from pydatalab.file_utils import get_file_info_by_id


class MRIBlock(DataBlock):
    blocktype = "mri"
    description = "In situ MRI"
    accepted_file_extensions = (".csv", "2dseq")

    @property
    def plot_functions(self):
        return (self.generate_mri_plot,)

    @classmethod
    def load_2dseq(
        self,
        location: str,
        image_size: tuple[int, int] = (512, 512),
    ) -> pd.DataFrame:
        if not isinstance(location, str):
            location = str(location)

        arrays = []
        with open(location, "rb") as f:
            while data := f.read():
                arr = np.frombuffer(data, dtype=np.dtype("<u2"))
                arrays.append(arr)

        image_arrays = []
        for arr in arrays:
            image_pixels = image_size[0] * image_size[1]
            num_images = arr.shape[0] // image_pixels
            for i in range(num_images):
                # grab an image_size square slice from arrays
                image_arrays.append(
                    arr[i * image_pixels : (i + 1) * image_pixels].reshape(*image_size)
                )

        return image_arrays

    def generate_mri_plots(self):
        file_info = get_file_info_by_id(self.data["file_id"], update_if_live=True)

        image_array = self.load_2dseq(
            file_info["location"],
        )
        from bokeh.layout import column
        from bokeh.models import ColumnDataSource, CustomJS, Slider
        from bokeh.plotting import figure

        p = figure(
            sizing_mode="scale_width",
            aspect_ratio=1,
            x_axis_label="",
            y_axis_label="",
        )

        image_source = ColumnDataSource(data={"image": [image_array[0]]})
        p.image(
            image="image",
            source=image_source,
            x=0,
            y=0,
            dw=10,
            dh=10,
            palette="Sunset11",
            level="image",
        )

        slider = Slider(start=0, end=len(image_array), step=1, value=0, title="Select image")

        slider_callback = CustomJS(
            args=dict(image_source=image_source, slider=slider),
            code="""
var selected_image_index = slider.value;
image_source.data["image"] = [image_arrays[selected_image_index]];
image_source.change.emit();
""",
        )
        slider.js_on_change("value", slider_callback)

        layout = column(slider, p)

        self.data["bokeh_plot_data"] = bokeh.embed.json_item(layout, theme=mytheme)
