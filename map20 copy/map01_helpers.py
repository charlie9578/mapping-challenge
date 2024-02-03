import requests

import matplotlib as mpl
import pandas as pd

from pyproj import Transformer
from bokeh.models import WMTSTileSource, ColumnDataSource, OpenURL, TapTool
from bokeh.palettes import Category10, viridis
from bokeh.plotting import figure, show

def get_om_data(overpass_query):
    """Get OpenMap data based on an overpass_query
     
    See these sources for details on the overpass_query
    https://janakiev.com/blog/openstreetmap-with-python-and-overpass-api/
    http://overpass-turbo.eu/
    https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL
    """
    

    
    overpass_url = "http://overpass-api.de/api/interpreter"

    response = requests.get(overpass_url, 
                            params={'data': overpass_query})
    data = response.json()
    
    return data



def get_om_wind_turbines(area="(55,-2,56,-1)"):
    """Get OpenMap wind farm data
    
    Parameters
    area=(south,west,north,east) in longitude and latitude as a string
    
    Returns 
    data dictionary
    """
    
    overpass_query = """
    [out:json];
    (node["generator:method"="wind_turbine"]"""+area+""";
     way["generator:method"="wind_turbine"]"""+area+""";
     rel["generator:method"="wind_turbine"]"""+area+""";
    );
    out center;
    """ 

    data = get_om_data(overpass_query)
    
    return data


def get_om_coordinates(data):
    
    coordinates=list()
    
    for element in data['elements']:
        coordinates.append((element['lat'],element['lon']))
    
    return coordinates

def get_om_latlon(data):
    
    lat=list()
    lon=list()
    
    for element in data['elements']:
        lat.append(element['lat'])
        lon.append(element['lon'])
    
    return lat,lon



def luminance(rgb):
    """Calculates the brightness of an rgb 255 color. See https://en.wikipedia.org/wiki/Relative_luminance

    Args:
        rgb(:obj:`tuple`): 255 (red, green, blue) tuple

    Returns:
        luminance(:obj:`scalar`): relative luminance

    Example:

        .. code-block:: python

            >>> rgb = (255,127,0)
            >>> luminance(rgb)
            0.5687976470588235

            >>> luminance((0,50,255))
            0.21243529411764706

    """

    luminance = (0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]) / 255

    return luminance


def color_to_rgb(color):
    """Converts named colors, hex and normalised RGB to 255 RGB values

    Args:
        color(:obj:`color`): RGB, HEX or named color

    Returns:
        rgb(:obj:`tuple`): 255 RGB values

    Example:

        .. code-block:: python

            >>> color_to_rgb("Red")
            (255, 0, 0)

            >>> color_to_rgb((1,1,0))
            (255,255,0)

            >>> color_to_rgb("#ff00ff")
            (255,0,255)
    """

    if isinstance(color, tuple):
        if max(color) > 1:
            color = tuple([i / 255 for i in color])

    rgb = mpl.colors.to_rgb(color)

    rgb = tuple([int(i * 255) for i in rgb])

    return rgb


def plot_points(df_points,
    tile_name="OpenMap",
    plot_width=800,
    plot_height=800,
    marker_size=14,
    kwargs_for_figure={},
    kwargs_for_marker={},
):
    """Plot the windfarm spatially on a map using the Bokeh plotting libaray.

    Args:
        asset_df(:obj:`pd.DataFrame`): PlantData.asset object containing the asset metadata.
        tile_name(:obj:`str`): tile set to be used for the underlay, e.g. OpenMap, ESRI, OpenTopoMap
        plot_width(:obj:`scalar`): width of plot
        plot_height(:obj:`scalar`): height of plot
        marker_size(:obj:`scalar`): size of markers
        kwargs_for_figure(:obj:`dict`): additional figure options for advanced users, see Bokeh docs
        kwargs_for_marker(:obj:`dict`): additional marker options for advanced users, see Bokeh docs. We have some custom behavior around the "fill_color" attribute. If "fill_color" is not defined, OpenOA will use an internally defined color pallete. If "fill_color" is the name of a column in the asset table, OpenOA will use the value of that column as the marker color. Otherwise, "fill_color" is passed through to Bokeh.

    Returns:
        Bokeh_plot(:obj:`axes handle`): windfarm map

    """

    # See https://wiki.openstreetmap.org/wiki/Tile_servers for various tile services
    MAP_TILES = {
        "OpenMap": WMTSTileSource(url="http://c.tile.openstreetmap.org/{Z}/{X}/{Y}.png"),
        "ESRI": WMTSTileSource(
            url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{Z}/{Y}/{X}.jpg"
        ),
        "OpenTopoMap": WMTSTileSource(url="https://tile.opentopomap.org/{Z}/{X}/{Y}.png"),
    }

    # Use pyproj to transform longitude and latitude into web-mercator and add to a copy of the asset dataframe
    TRANSFORM_4326_TO_3857 = Transformer.from_crs("EPSG:4326", "EPSG:3857")

    df_points["x"], df_points["y"] = TRANSFORM_4326_TO_3857.transform(
        df_points["lat"], df_points["lon"]
    )
    df_points["coordinates"] = tuple(zip(df_points["lat"], df_points["lon"]))

    # Define default and then update figure and marker options based on kwargs
    figure_options = {
        "tools": "save,hover,pan,tap,wheel_zoom,reset,help",
        "x_axis_label": "Longitude",
        "y_axis_label": "Latitude",
        "match_aspect": True,
        "tooltips": [("nodeId", "@id"), 
                     ("plantName", "@name"), 
                     ("source", "@source"), 
                     ("capacity MW", "@generator_output_electricity"), 
                     ("COD", "@start_date"),
                     ("hub_height", "@height_hub"),
                     ("type", "@generator_type"),
                     ("rotor_diameter", "@rotor_diameter"),
                     ("manufacturer", "@manufacturer"),
                     ("model", "@model"),
                     ("(Lat,Lon)", "@coordinates")],
    }
    figure_options.update(kwargs_for_figure)

    marker_options = {
        "marker": "circle_y",
        "line_width": 1,
        "alpha": 0.8,
        "fill_color": "data_rank_colour",
        "line_color": "auto_line_color",
        "legend_group": "data_rank",
    }
    marker_options.update(kwargs_for_marker)

    # Create an appropriate fill color map and contrasting line color
    if marker_options["fill_color"] == "auto_fill_color":
        color_grouping = marker_options["legend_group"]

        df_points = df_points.sort_values(color_grouping)

        if len(set(df_points[color_grouping])) <= 10:
            color_palette = list(Category10[10])
        else:
            color_palette = viridis(len(set(df_points[color_grouping])))

        color_mapping = dict(zip(set(df_points[color_grouping]), color_palette))
        df_points["auto_fill_color"] = df_points[color_grouping].map(color_mapping)
        df_points["auto_fill_color"] = df_points["auto_fill_color"].apply(color_to_rgb)
        df_points["auto_line_color"] = [
            "black" if luminance(color) > 0.5 else "white" for color in df_points["auto_fill_color"]
        ]

    else:
        if marker_options["fill_color"] in df_points.columns:
            df_points[marker_options["fill_color"]] = df_points[marker_options["fill_color"]].apply(
                color_to_rgb
            )
            df_points["auto_line_color"] = [
                "black" if luminance(color) > 0.5 else "white"
                for color in df_points[marker_options["fill_color"]]
            ]

        else:
            df_points["auto_line_color"] = "black"

    # Create the bokeh data source
    source = ColumnDataSource(df_points)

    # Create a bokeh figure with tiles
    plot_map = figure(
        width=plot_width,
        height=plot_height,
        x_axis_type="mercator",
        y_axis_type="mercator",
        **figure_options,
    )

    plot_map.add_tile(MAP_TILES[tile_name])

    # Plot the asset devices
    renderer = plot_map.scatter(x="x", y="y", source=source, size=marker_size, **marker_options)

    renderer.selection_glyph = None
    renderer.nonselection_glyph = None

    url = "https://www.openstreetmap.org/node/@id/"
    taptool = plot_map.select(type=TapTool)
    taptool.callback = OpenURL(url=url)

    return plot_map


if __name__ == "__main__":
    
    import re
    import numpy as np

    try:
        df_turbines = pd.read_csv("turbines_offshore.csv")
    except:
        turbines = get_om_wind_turbines(area="(51.4,2.6,51.9,3.2)")
        df_turbines = pd.json_normalize(turbines['elements'])
        df_turbines.to_csv("turbines_offshore.csv")

    df_turbines_expanded = df_turbines.rename(columns=lambda x: re.sub(':','_',x))
    df_turbines_expanded = df_turbines_expanded.rename(columns=lambda x: re.sub('tags.','',x))

    required_columns = set(["source","generator_output_electricity","start_date","height_hub","generator_type","rotor_diameter","manufacturer","model","offshore","floating"])
    missing_columns = list(required_columns - set(df_turbines_expanded.columns))

    df_turbines_expanded[missing_columns] = np.nan

    # drop un-required columns
    full_data_list = ["id","name","source","lat","lon","source","generator_output_electricity","start_date","height_hub","generator_type","rotor_diameter","manufacturer","model","offshore","floating"]
    df_turbines_expanded = df_turbines_expanded[full_data_list]


    df_turbines_expanded["data_rank_colour"] = "sienna"
    df_turbines_expanded["data_rank"] = "Bronze"

    gold_data_list = ["source","generator_output_electricity","start_date","height_hub","generator_type","rotor_diameter","manufacturer","model","offshore","floating"]
    silver_data_list = ["height_hub","rotor_diameter"]

    df_turbines_expanded[silver_data_list].isnull().sum(axis=1)

    df_turbines_expanded.loc[df_turbines_expanded[silver_data_list].isnull().sum(axis=1)==0,"data_rank_colour"] = "silver"
    df_turbines_expanded.loc[df_turbines_expanded[silver_data_list].isnull().sum(axis=1)==0,"data_rank"] = "Silver"

    df_turbines_expanded[gold_data_list].isnull().sum(axis=1)

    df_turbines_expanded.loc[df_turbines_expanded[gold_data_list].isnull().sum(axis=1)==0,"data_rank_colour"] = "gold"
    df_turbines_expanded.loc[df_turbines_expanded[gold_data_list].isnull().sum(axis=1)==0,"data_rank"] = "Gold"

    map = plot_points(df_turbines_expanded)

    map.title.text = "Wind turbines in OpenStreetMap, ranked by OSM metadata quality"
    
    show(map)
