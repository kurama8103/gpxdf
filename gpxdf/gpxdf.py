import os
import pandas as pd
import folium
import fitparse
import gpxpy
from geopy import distance
import numpy as np
import warnings
warnings.simplefilter('ignore', FutureWarning)

def read_fit(fit_file_path: str):
    fitfile = fitparse.FitFile(fit_file_path)
    data = [record.get_values() for record in fitfile.get_messages("record")]
    return data


def read_gpx(file):
    # parse
    gpx_file = open(file, "r", encoding="utf-8")
    return gpxpy.parse(gpx_file)


def gpx_to_df(gpx: gpxpy.gpx.GPX):
    gpx_list = []
    for p in gpx.get_points_data():
        gpx_list.append(
            [
                p.point.latitude,
                p.point.longitude,
                p.point.elevation,
                p.point.time,
                p.distance_from_start,
                p.track_no,
                p.segment_no,
                p.point_no,
            ]
        )
    colname = [
        "latitude",
        "longitude",
        "elevation",
        "time",
        "distance_from_start",
        "track_no",
        "segment_no",
        "point_no",
    ]
    df = pd.DataFrame(gpx_list, columns=colname)
    t = pd.to_datetime(df["time"], utc=True)  # UTC
    df["time"] = t.dt.tz_convert("Asia/Tokyo")
    df = add_velocity(df, cut_upper_velo=70)
    df["trackname"] = gpx.name
    return df


def df_to_gpx(df):
    df["time"] = df["time"].dt.tz_convert("utc")
    gpxcls = gpxpy.gpx.GPX()
    gpx_track = gpxpy.gpx.GPXTrack()
    gpxcls.tracks.append(gpx_track)
    gpx_segment = gpxpy.gpx.GPXTrackSegment()
    gpx_track.segments.append(gpx_segment)
    gpx_segment.points = df.apply(_df_to_GPXTrackPoint, axis=1).to_list()
    return gpxcls


def _df_to_GPXTrackPoint(row):
    return gpxpy.gpx.GPXTrackPoint(
        row["latitude"],
        row["longitude"],
        elevation=row["elevation"],
        time=row["time"].to_pydatetime(),
    )


def df_to_html_map(df, filename_html: str = None, zoom_start: int = 10):
    df_t = df[["latitude", "longitude"]]
    map_ = folium.Map(
        location=(df_t.max() + df_t.min()) / 2,
        zoom_start=zoom_start,
    )

    for t, _d in df.groupby("trackname"):
        folium.PolyLine(_d[["latitude", "longitude"]].dropna(), tooltip=t).add_to(map_)
        cum = _d.iloc[-1].get("distance_from_start", 0)
        des = t + " " + str(int(cum // 1000)) + "km"
        folium.Marker(
            location=_d[["latitude", "longitude"]].dropna().iloc[-1],
            popup=folium.Popup(des, parse_html=True),
            icon=folium.Icon(color="green", icon="ok-circle"),
        ).add_to(map_)

    if filename_html:
        map_.save(filename_html)
    return map_


def add_velocity(df_gpx, cut_upper_velo: float = None):
    df_t = pd.DataFrame()
    df_t["diff_time"] = df_gpx["time"].diff()
    df_t["distance"] = distance_from_df(df_gpx[["latitude", "longitude"]].ffill())
    df_t["velocity"] = df_t["distance"] / df_t["diff_time"].dt.seconds * 3.6
    if cut_upper_velo:
        df_t["velocity"] = df_t["velocity"].clip(upper=cut_upper_velo)
    return pd.concat([df_gpx, df_t], axis=1)


def distance_from_df(df_lat_lon):
    _d = np.hstack((df_lat_lon[1:], df_lat_lon[:-1]))
    v = np.insert(
        np.apply_along_axis(
            lambda x: distance.distance((x[0], x[1]), (x[2], x[3])).meters, 1, _d
        ),
        0,
        0,
    )
    return v


def divine_list(list_, cut):
    conditions = [list_ < i for i in cut]
    return np.select(conditions, range(len(conditions)), default=len(cut))


class GPSDF(gpxpy.gpx.GPX):
    def __init__(self, path):
        super().__init__()
        self.path = path
        self.ext = os.path.splitext(path)[1]
        self.df = pd.DataFrame()
        try:
            if self.ext == ".gpx":
                self.tracks = read_gpx(self.path).tracks
                self.name = os.path.basename(self.path)
                self.df_raw = gpx_to_df(self)
                self.df = self.df_raw.copy()
            elif self.ext == ".fit":
                self.df_raw = pd.DataFrame(read_fit(self.path))
                self.df = self.df_raw.dropna(
                    subset=["position_lat", "position_long"]
                ).copy()
                self.df.rename(
                    columns={"timestamp": "time", "altitude": "elevation"}, inplace=True
                )
                self.df[["latitude", "longitude"]] = self.df[
                    ["position_lat", "position_long"]
                ] * (180 / 2**31)
                self.df["time"] = pd.to_datetime(self.df["time"], utc=True)  # UTC
                self.tracks = df_to_gpx(self.df).tracks
                self.name = os.path.basename(self.path)
                self.df = gpx_to_df(self)
            # self.df["time"] = t.dt.tz_convert("Asia/Tokyo")
            # t = pd.to_datetime(self.df["time"], utc=True)  # UTC
        except Exception as e:
            print("error: ", path, ":", e)

    def to_html_map(self, filename="map.html", zoom_start=8):
        return df_to_html_map(self.df, filename, zoom_start)

    def simplify_(self):
        if self.get_points_no():
            a = self.get_points_no()
            self.simplify()
            self.df = gpx_to_df(self)
            b = self.get_points_no()
            print(" {:.1%} reduce".format(1 - b / a), "(from", a, "to", b, ")")

    def divide_by_criteria(self, criteri_time="4hours"):
        cut = self.df[self.df["diff_time"].abs() > criteri_time].index
        if len(cut) > 0:
            self.df["trackname"] = (
                self.df["trackname"] + "_" + divine_list(self.df.index, cut).astype(str)
            )
