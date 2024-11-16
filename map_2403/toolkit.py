import requests

import json

import pandas as pd

from bokeh.plotting import figure
from bokeh.models import WMTSTileSource
from bokeh.models import ColumnDataSource
from bokeh.palettes import viridis, Category10

from pyproj import Transformer

import matplotlib

import time

from requests.packages.urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter


def osm_overpass_query(overpass_query):
    """Get OpenMap data based on an overpass_query
     
    See these sources for details on the overpass_query
    https://janakiev.com/blog/openstreetmap-with-python-and-overpass-api/
    http://overpass-turbo.eu/
    https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL
    """
    
    overpass_url = "http://overpass-api.de/api/interpreter"

    s = requests.Session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[429,504])
    s.mount('http://', HTTPAdapter(max_retries=retries))

    response = s.get(overpass_url, 
        params={'data': overpass_query},
        headers={'Referer':'https://github.com/charlie9578/openstreetmap-mapping',
        'User-agent': 'https://github.com/charlie9578/openstreetmap-mapping'})

    try:
        data = response.json()
    except:
        print(response)

    return data
                

def get_osm_data(key="amenity",tag="post_box",area="(55,-2,56,-1)",output="center",recursion="",element=""):
    """Get OpenMap key:tag nodes in a given area
    
    Parameters::
    key
    tag
    area=(south,west,north,east) in longitude and latitude as a string
    output: center=return the centre of the way points, geom=returns all node lat/lons
    
    Returns::
    dataframe
    """

    if element != "":
        overpass_query = """
        [out:json];
        (
        """+element+"""[\""""+str(key)+"""\"=\""""+str(tag)+"""\"]"""+area+""";
        """+recursion+"""
        );
        out """+output+""";
        """ 

    else:
        overpass_query = """
        [out:json];
        (
        node[\""""+str(key)+"""\"=\""""+str(tag)+"""\"]"""+area+""";
        way[\""""+str(key)+"""\"=\""""+str(tag)+"""\"]"""+area+""";
        rel[\""""+str(key)+"""\"=\""""+str(tag)+"""\"]"""+area+""";
        """+recursion+"""
        );
        out """+output+""";
        """ 

    #print(overpass_query)

    data = osm_overpass_query(overpass_query)

    #print(data)
    
    elements = data['elements']

    #print(elements)

    if elements:
        df = pd.DataFrame.from_records(elements)

        df[pd.DataFrame.from_records(df['tags']).columns] = pd.DataFrame.from_records(df['tags'])

        if 'center' in df.columns:
            df.loc[df['center'].notnull(),['lat','lon']] = pd.DataFrame.from_records(list(df[df['center'].notnull()]['center'])).set_index(df.loc[df['center'].notnull()].index)
    
        if 'geometry' in df.columns:
            df.loc[df['geometry'].notnull(),['lat','lon']] = pd.DataFrame.from_records(df.loc[df['geometry'].notnull(),'geometry'].map(lambda cell: pd.DataFrame.from_records(cell).mean()))

    else:
        print("No specified nodes found in area")
        df = pd.DataFrame()

    df['key'] = key
    df['tag'] = tag
    
    return df


def get_osm_id_data(member_id="5574761791",obj_type="node",output="center",recursion=""):
    
    
    overpass_query = """
    [out:json];
    (
    """+obj_type+"""("""+str(member_id)+""");
        """+recursion+"""
    );

    out """+output+""";
    """ 

    #print(overpass_query)

    data = osm_overpass_query(overpass_query)

    return data

    

def get_osm_data_by_id(member_id="5574761791",obj_type="node",output="center",recursion=""):
    """Get OpenMap key:tag nodes in a given area
    
    Parameters::
    type = node, way, or rel/relation
    tag
    area=(south,west,north,east) in longitude and latitude as a string
    output: center=return the centre of the way points, geom=returns all node lat/lons
    
    Returns::
    dataframe
    """

    overpass_query = """
    [out:json];
    (
    """+obj_type+"""("""+str(member_id)+""");
        """+recursion+"""
    );
    
    out """+output+""";
    """ 

    #print(overpass_query)

    data = osm_overpass_query(overpass_query)

    #print(data)
    
    elements = data['elements']

    #print(elements)

    if elements:
        df = pd.DataFrame.from_records(elements)
        df = df.dropna(subset=['tags'])

        if 'tags' in df.columns:
            df[pd.DataFrame.from_records(df['tags']).columns] = pd.DataFrame.from_records(df['tags'])

        if 'center' in df.columns:
            df.loc[df['center'].notnull(),['lat','lon']] = pd.DataFrame.from_records(list(df[df['center'].notnull()]['center'])).set_index(df.loc[df['center'].notnull()].index)
    
        if 'geometry' in df.columns:
            df.loc[df['geometry'].notnull(),['lat','lon']] = pd.DataFrame.from_records(df.loc[df['geometry'].notnull(),'geometry'].map(lambda cell: pd.DataFrame.from_records(cell).mean()))

    else:
        print("No specified nodes found in area")
        df = pd.DataFrame()
    
    return df


def get_osm_wind_turbines(area="(55,-2,49.7564, -2.0895)"):
    """Get OpenMap wind turbine data
    
    Parameters::
    area=(south,west,north,east) in longitude and latitude as a string
    
    Returns::
    data dictionary
    """
  
    df = get_osm_data(key="generator:method",tag="wind_turbine",area=area)

    return df


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

    luminance = (0.2126*rgb[0] + 0.7152*rgb[1] + 0.0722*rgb[2])/255

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
            color = tuple([i/255 for i in color])

    rgb = matplotlib.colors.to_rgb(color)

    rgb = tuple([int(i*255) for i in rgb])

    return rgb




def plot_latlon(df,tile_name="ESRI",plot_width=800,plot_height=800,marker_size=14,kwargs_for_figure={},kwargs_for_marker={}):

    """Plot the df on a map

    Args:
        df(:obj:`plant object`): project to be plotted, must include lat, lon, tags
        tile_name(:obj:`str`): tile set to be used for the underlay, e.g. OpenMap, ESRI, OpenTopoMap
        plot_width(:obj:`scalar`): width of plot
        plot_height(:obj:`scalar`): height of plot
        marker_size(:obj:`scalar`): size of markers
        kwargs_for_figure(:obj:`dict`): additional figure options for advanced users, see Bokeh docs
        kwargs_for_marker(:obj:`dict`): additional marker options for advanced users, see Bokeh docs
 
    Returns:
        Bokeh_plot(:obj:`axes handle`): map of coordinates

    Example:
        .. bokeh-plot::

            import pandas as pd

            from bokeh.plotting import show


            # Create the bokeh wind farm plot
            show(plot_latlon(map_df,tile_name="ESRI",plot_width=600,plot_height=600))
    """


    # See https://wiki.openstreetmap.org/wiki/Tile_servers for various tile services
    MAP_TILES = {"OpenMap": WMTSTileSource(url="http://c.tile.openstreetmap.org/{Z}/{X}/{Y}.png"),
             "ESRI": WMTSTileSource(url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{Z}/{Y}/{X}.jpg"),
             "OpenTopoMap": WMTSTileSource(url="https://tile.opentopomap.org/{Z}/{X}/{Y}.png")}


    # Use pyproj to transform longitude and latitude into web-mercator and add to a copy of the asset dataframe
    TRANSFORM_4326_TO_3857 = Transformer.from_crs("EPSG:4326", "EPSG:3857")
    
    map_df = df.copy()
    
    map_df["x"],map_df["y"] = TRANSFORM_4326_TO_3857.transform(map_df['lat'],map_df['lon'])   
    map_df["coordinates"]=tuple(zip(map_df["lat"],map_df["lon"]))
    map_df['tags'] = map_df['tags'].apply(str)
    map_df['tag'] = map_df['tag'].apply(str)
    map_df['key'] = map_df['key'].apply(str)

    # Define default and then update figure and marker options based on kwargs
    figure_options = {"tools":"save,hover,tap,pan,wheel_zoom,reset,help",
        "x_axis_label":"lat",
        "y_axis_label":"lat",
        "match_aspect":True,
        "tooltips":[("id", "@id"),("key", "@key"),("tag", "@tag"),("tags", "@tags"),("(lat,lon)", "@coordinates")]
        }
    figure_options.update(kwargs_for_figure)

    marker_options = {"marker":"circle_y",
        "line_width":1,
        "alpha":0.8,
        "fill_color":"auto_fill_color",
        "line_color":"auto_line_color",
        "legend_group":"tag",
        }
    marker_options.update(kwargs_for_marker)        
    
    
    # Create an appropriate fill color map and contrasting line color
    if marker_options["fill_color"] == "auto_fill_color":
        color_grouping = marker_options["legend_group"]

        map_df = map_df.sort_values(color_grouping)

        if len(set(map_df[color_grouping]))<=10:
            color_palette = list(Category10[10])
        else:
            color_palette = viridis(len(set(map_df[color_grouping])))

        color_mapping = dict(zip(set(map_df[color_grouping]),color_palette))
        map_df["auto_fill_color"] = map_df[color_grouping].map(color_mapping)
        map_df["auto_fill_color"] = map_df["auto_fill_color"].apply(color_to_rgb)
        map_df["auto_line_color"] = ["black" if luminance(color)>0.5 else "white" for color in map_df["auto_fill_color"]]
        #print(map_df["auto_fill_color"])

    else:
        if marker_options["fill_color"] in map_df.columns:
            map_df[marker_options["fill_color"]] = map_df[marker_options["fill_color"]].apply(color_to_rgb)
            map_df["auto_line_color"] = ["black" if luminance(color)>0.5 else "white" for color in map_df[marker_options["fill_color"]]]
            #print(marker_options["fill_color"])

        else:
            map_df["auto_line_color"] = "black"
            #print(marker_options["fill_color"])


    
    # Create a bokeh figure with tiles
    plot_map = figure(plot_width=plot_width, plot_height=plot_height,
                    x_axis_type="mercator", y_axis_type="mercator",
                    **figure_options)
    
    plot_map.add_tile(MAP_TILES[tile_name])


    # Plot the asset devices
    for legend_group in set(map_df[marker_options["legend_group"]]):

        source = ColumnDataSource(map_df.loc[map_df[marker_options["legend_group"]]==legend_group])

        marker_options_plot = marker_options.copy()

        marker_options_plot["legend_label"] = legend_group
        del marker_options_plot["legend_group"]

        plot_map.scatter(x="x", y="y",
            source=source,
            size=marker_size,
            **marker_options_plot)


    return plot_map


def get_osm_kvs():
    
    kvs = dict()

    for page in range(100):

        url = r"https://taginfo.openstreetmap.org/api/4/projects/tags?sortname=count_all&sortorder=desc&page="+str(page+1)+r"&rp=100&qtype=tags&format=json_pretty"

        resp = requests.get(url)

        string = resp.text

        d = json.loads(string)

        for kv_pair in d['data']:
            
            if 'value' in kv_pair.keys():
                
                kv_pair['key'] = kv_pair['key'].replace(':', '__')
                kv_pair['value'] = kv_pair['value'].replace(':', '__')
                
                if kv_pair['key'] in kvs.keys():
                    kvs[kv_pair['key']][kv_pair['value']] = {'value':kv_pair['value']}

                else:
                    kvs[kv_pair['key']] = dict()
                    kvs[kv_pair['key']]['value'] = kv_pair['key']
                    kvs[kv_pair['key']][kv_pair['value']] = {'value':kv_pair['value']}

       
    return kvs