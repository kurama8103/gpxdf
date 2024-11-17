# GPXファイルをPandas DataFrameで扱う

* Install  
`pip3 install git+https://github.com/kurama8103/gpxdf`

## ファイル読み込みと計算
* GPXファイルを読み込み、pd.DataFrameに変換  
`import gpxdf`  
`df = gpxdf.read_gpx('read.gpx')`

* dfの緯度経度と時間を基に速度を計算  
`df = gpxdf.add_velocity(df)`

## データ活用
* 速度推移グラフ(matplotlib)  
`import matplotlib.plot as plt`  
`plt.plot(df.query('velocity!=inf')['velocity'])`

* 経路イメージ  
`plt.plot(df.longitude, df.latitude)`

* 経路をマップに表示するhtmlを作成(foliumライブラリ使用)  
`gpxdf.df_to_html_map(df, 'map.html')`
