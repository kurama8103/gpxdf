from datetime import timedelta
import gpxpy
import pandas as pd
from geopy.distance import distance
import xml.etree.ElementTree as ET
from xml.dom import minidom
import folium
import fitparse
import os


def read_gpx(filename):
    # parse
    gpx_file = open(filename, 'r', encoding='utf-8')
    gpx_p = gpxpy.parse(gpx_file)

    gpx_list = []
    # tonlist
    for track in gpx_p.tracks:
        for i, segment in enumerate(track.segments):
            for point in segment.points:
                gpx_list.append([point.latitude, point.longitude,
                                 point.elevation, point.time, track.name, i])
    # to pd.DataFrame
    colname = ['latitude', 'longitude',
               'elevation', 'time', 'trackname', 'segment_no']
    df = pd.DataFrame(gpx_list, columns=colname)
    df['time'] = pd.to_datetime(df['time'], utc=True)  # UTC

    # Adjust trackname
    if df.trackname.isnull().all():
        df.trackname = gpx_file.name.replace('.gpx', '')

    return df


def add_velocity(df_gpx):
    df_t = pd.DataFrame()
    # time difference
    df_t['diff_time'] = df_gpx.time.diff()
    # distance
    df_t['distance'] = distance_df(df_gpx[['latitude', 'longitude']])
    # velocity
    df_t['velocity'] = df_t['distance'] / df_t['diff_time'].dt.seconds*3.6
    return pd.concat([df_gpx, df_t], axis=1)


def distance_df(df_gpx):
    # Vincenty
    return pd.concat([df_gpx, df_gpx.shift()], axis=1).dropna().apply(
        lambda x: distance((x[0], x[1]), (x[2], x[3])).meters, axis=1)


def to_gpx(df, filename=None):
    # create gpx file and return gpx text (if filename=None)

    # to gpx data
    gpx = ET.Element('gpx', {'version': '1.1', 'creator': 'owner'})

    trk_n = None
    seg_no = None

    try:
        df.trackname
    except:
        df['trackname'] = None
    try:
        df.segment_no
    except:
        df['segment_no'] = None

    for i, row in df.iterrows():
        # track
        if row.trackname != trk_n:
            trk = ET.SubElement(gpx, 'trk')
            trkname = ET.SubElement(trk, 'name')
            trkname.text = row.trackname
        trk_n = row.trackname

        # segment
        if row.segment_no != seg_no:
            trkseg = ET.SubElement(trk, 'trkseg')
        seg_no = row.segment_no

        # point
        trkpt = ET.SubElement(trkseg, 'trkpt', {'lon': str(
            row.longitude), 'lat': str(row.latitude)})
        ele = ET.SubElement(trkpt, 'ele')
        ele.text = str(row.elevation)
        time = ET.SubElement(trkpt, 'time')
        time.text = str(row.time).replace(' ', 'T').replace('+00:00', 'Z')

        # to gpx xml
        rough_string = ET.tostring(gpx)
        reparsed = minidom.parseString(rough_string)

    if filename == None:
        return print(reparsed.toprettyxml(indent='  '))
    else:
        reparsed.writexml(
            open(filename, mode='w'),
            encoding='utf-8',
            newl="\n",
            indent="",
            addindent="\t"
        )


def to_html_map(df, filename='map.html', zoom_start=6):
    df_t = df[['latitude', 'longitude']]
    map_ = folium.Map(
        location=(df_t.iloc[0]+df_t.iloc[-1])/2, zoom_start=zoom_start)
    [folium.PolyLine(df[['latitude', 'longitude']]).add_to(map_)
     for t, df in df.dropna().groupby('trackname')]
    map_.save(filename)


def read_fit(filename):
    # Load the FIT file
    fitfile = fitparse.FitFile(filename)

    list_ = []
    for record in fitfile.get_messages("record"):
        d = {}
        for data in record:
            d[data.name] = data.value
        list_.append(d)
    df_ = pd.DataFrame(list_)
    df_['trackname'] = os.path.splitext(filename)[0]
    return df_


def fit_to_gpx_df(df_fit):
    df = pd.DataFrame()
    df['latitude'] = df_fit['position_lat']*180/(2**31)
    df['longitude'] = df_fit['position_long']*180/(2**31)
    df['elevation'] = df_fit['enhanced_altitude']
    df['time'] = pd.to_datetime(df_fit['timestamp'], utc=True)  # UTC
    df['trackname'] = df_fit['trackname']
    df['diff_time'] = df_fit['timestamp'].diff()
    df['distance'] = distance_df(df[['latitude', 'longitude']])
    df['velocity'] = df['distance'] / df['diff_time'].dt.seconds*3.6
    return df


def gpx_sammary(df, cut_velocity=1):
    if df['diff_time'].dtypes.name != 'timedelta64[ns]':
        df['diff_time'] = pd.to_timedelta(df['diff_time'])

    dic_ = {}
    dic_['trackname'] = df['trackname'].unique()[0]
    dic_['total_distance'] = df['distance'].sum()/1000
    dic_['moving_time'] = df.query(
        'velocity>=@cut_velocity')['diff_time'].sum()
    dic_['moving_hours'] = dic_['moving_time']/timedelta(hours=1)
    dic_['avg_velocity'] = dic_['total_distance'] / dic_['moving_hours']
    return dic_


class GPSDF:
    def __init__(self, path):
        self.ext = os.path.splitext(path)[1]
        if self.ext == '.gpx':
            self.df_raw = read_gpx(path)
            self.df = add_velocity(self.df_raw)
        elif self.ext == '.fit':
            self.df_raw = read_fit(path)
            self.df = fit_to_gpx_df(self.df_raw)

    def to_gpx(self, filename=None):
        return to_gpx(self.df, filename)

    def to_html_map(self, filename='map.html', zoom_start=8):
        return to_html_map(self.df, filename, zoom_start)
