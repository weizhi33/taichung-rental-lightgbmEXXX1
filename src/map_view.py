from __future__ import annotations

import json
import os
from functools import lru_cache

import geopandas as gpd
import numpy as np
import pandas as pd  

from .config import DATA_PATH, EPSG_WEB

# 1. 這裡就是剛剛不見的 MAP_CENTER！
MAP_CENTER = (24.9930, 121.3010)

def _red_color(value: float, vmin: float, vmax: float) -> str:
    palette = ["#fee5d9", "#fcbba1", "#fc9272", "#fb6a4a", "#de2d26", "#a50f15"]
    if not np.isfinite(value) or vmax <= vmin:
        return palette[2]
    frac = min(max((value - vmin) / (vmax - vmin), 0.0), 1.0)
    return palette[min(int(frac * len(palette)), len(palette) - 1)]

@lru_cache(maxsize=1)
def load_map_gdf() -> gpd.GeoDataFrame:
    gdf = gpd.read_file(DATA_PATH)
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
    if gdf.crs is None:
        gdf = gdf.set_crs(3826)
    gdf = gdf.to_crs(EPSG_WEB)
    
    # 2. 為了讓地圖可以篩選，把會用到的條件欄位也抓進來
    cols_needed = [
        "鄉鎮市",
        "鄉鎮市區",  # 為了相容不同的命名習慣
        "建物型",
        "總樓層",
        "總價元",
        "單價元",
        "有無管理組織",
        "電梯",
        "車位類別", 
        "geometry",
    ]
    gdf = gdf[[col for col in cols_needed if col in gdf.columns]].copy()

    max_points = int(os.environ.get("APP_MAP_MAX_POINTS", "15000") or "0")
    if max_points > 0 and len(gdf) > max_points:
        gdf = gdf.sample(max_points, random_state=42).copy()
    return gdf

@lru_cache(maxsize=1)
def map_geojson() -> tuple[dict, float, float]:
    gdf = load_map_gdf()
    
    gdf["總價元"] = pd.to_numeric(gdf["總價元"], errors='coerce').fillna(0)
    
    vmin = float(gdf["總價元"].quantile(0.02))
    vmax = float(gdf["總價元"].quantile(0.98))
    gdf = gdf.copy()
    
    gdf["_color"] = gdf["總價元"].apply(lambda value: _red_color(float(value), vmin, vmax))
    return json.loads(gdf.to_json(drop_id=True)), vmin, vmax

def _format_value(value) -> str:
    if value is None:
        return ""
    try:
        if np.isnan(value):
            return ""
    except TypeError:
        pass
    if isinstance(value, float):
        return f"{value:,.0f}" 
    return str(value)

def _popup_html(properties: dict) -> str:
    labels = {
        "鄉鎮市": "鄉鎮市",
        "鄉鎮市區": "鄉鎮市",
        "建物型": "建物型態",
        "總樓層": "總樓層",
        "總價元": "總價 (元)",
        "單價元": "單價 (元/平方公尺)",
        "電梯": "電梯",
        "有無管理組織": "管理組織"
    }
    rows = []
    for key, label in labels.items():
        if key in properties:
            rows.append(
                f"<tr><th style='text-align:left;padding:2px 8px 2px 0'>{label}</th>"
                f"<td style='text-align:right;padding:2px 0'>{_format_value(properties[key])}</td></tr>"
            )
    return "<table style='font-size:12px'>" + "".join(rows) + "</table>"

# 3. 接收從 UI 傳過來的篩選變數
def create_leafmap_widget(
    lat_state, 
    lon_state, 
    target_district=None, 
    target_parking=None, 
    target_elevator=None,
    target_management=None
):
    import leafmap
    from ipyleaflet import GeoJSON, Marker, Popup
    from ipywidgets import HTML

    data, _vmin, _vmax = map_geojson()
    
    # 4. 在這裡執行地圖點點的篩選邏輯
    features = data.get("features", [])
    filtered_features = []
    
    for f in features:
        props = f.get("properties", {})
        keep = True
        
        # 判斷行政區
        town_name = props.get("鄉鎮市") or props.get("鄉鎮市區")
        if target_district and target_district.value != "全部" and town_name != target_district.value:
            keep = False
            
        # 判斷管理組織
        if target_management and target_management.value != "不拘":
            if str(props.get("有無管理組織")) != target_management.value:
                keep = False
                
        # 判斷電梯
        if target_elevator and target_elevator.value != "不拘":
            if str(props.get("電梯")) != target_elevator.value:
                keep = False
        
        # 判斷車位 (有字串代表有車位，NaN代表無)
        if target_parking and target_parking.value != "不拘":
            has_park = "有" if pd.notna(props.get("車位類別")) and str(props.get("車位類別")).strip() != "" else "無"
            if has_park != target_parking.value:
                keep = False

        if keep:
            filtered_features.append(f)
            
    filtered_data = {"type": "FeatureCollection", "features": filtered_features}

    map_height = os.environ.get("APP_MAP_HEIGHT", "calc(100vh - 96px)")

    m = leafmap.Map(center=MAP_CENTER, zoom=12, height=map_height)
    m.layout.width = "100%"
    m.layout.height = map_height
    m.layout.min_height = "760px"
    try:
        m.add_basemap("OpenStreetMap")
    except Exception:
        pass

    def style_callback(feature):
        properties = feature.get("properties", {})
        return {
            "radius": 4,
            "color": "#7f1d1d",
            "weight": 0.5,
            "fillColor": properties.get("_color", "#fb6a4a"),
            "fillOpacity": 0.72,
        }

    houses_layer = GeoJSON(
        data=filtered_data,
        name="Taoyuan Houses",
        style_callback=style_callback,
        point_style={"radius": 4, "fillOpacity": 0.72, "weight": 0.5},
        hover_style={"fillOpacity": 1.0, "weight": 1.5},
    )
    m.add_layer(houses_layer)

    marker = Marker(location=(lat_state.value, lon_state.value), draggable=True, title="Target house")
    m.add_layer(marker)
    popup = Popup(location=(lat_state.value, lon_state.value), close_button=True, auto_close=True, close_on_escape_key=True)

    def set_target(lat: float, lon: float):
        marker.location = (float(lat), float(lon))
        lat_state.value = float(lat)
        lon_state.value = float(lon)

    def sync_marker(change):
        if change.get("name") == "location":
            lat, lon = change["new"]
            lat_state.value = float(lat)
            lon_state.value = float(lon)

    marker.observe(sync_marker, names="location")

    def handle_map_click(**kwargs):
        if kwargs.get("type") == "click" and kwargs.get("coordinates"):
            lat, lon = kwargs["coordinates"]
            set_target(lat, lon)

    def handle_house_click(**kwargs):
        feature = kwargs.get("feature") or {}
        geometry = feature.get("geometry") or {}
        coords = geometry.get("coordinates")
        if coords and len(coords) >= 2:
            lon, lat = coords[:2]
            set_target(lat, lon)
            popup.location = (float(lat), float(lon))
        popup.child = HTML(value=_popup_html(feature.get("properties", {})))
        if popup not in m.layers:
            m.add_layer(popup)

    m.on_interaction(handle_map_click)
    houses_layer.on_click(handle_house_click)
    try:
        m.add_layer_control()
    except Exception:
        pass
    return m