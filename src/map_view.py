from __future__ import annotations

import json
import os
from functools import lru_cache

import geopandas as gpd
import numpy as np
import pandas as pd  

from .config import DATA_PATH, EPSG_WEB

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
    
    # 🌟【超級防呆】只要欄位名字裡面有這些關鍵字，通通保留，避免被 GPKG 截斷而找不到！
    keep_cols = ["geometry"]
    for col in gdf.columns:
        if any(keyword in col for keyword in ["鄉鎮", "建物", "樓層", "價", "管", "電梯", "車位", "建築", "單價"]):
            keep_cols.append(col)
    
    gdf = gdf[list(set(keep_cols))].copy()

    max_points = int(os.environ.get("APP_MAP_MAX_POINTS", "15000") or "0")
    if max_points > 0 and len(gdf) > max_points:
        gdf = gdf.sample(max_points, random_state=42).copy()
    return gdf

@lru_cache(maxsize=1)
def map_geojson() -> tuple[dict, float, float]:
    gdf = load_map_gdf()
    
    # 抓出總價欄位（可能是總價元或總價）
    price_col = "總價元" if "總價元" in gdf.columns else "總價"
    if price_col not in gdf.columns:
        # 如果真的找不到，就隨便抓個數字欄位墊檔避免當機
        price_col = [c for c in gdf.columns if "價" in c][0] 

    gdf[price_col] = pd.to_numeric(gdf[price_col], errors='coerce').fillna(0)
    vmin = float(gdf[price_col].quantile(0.02))
    vmax = float(gdf[price_col].quantile(0.98))
    gdf = gdf.copy()
    
    gdf["_color"] = gdf[price_col].apply(lambda value: _red_color(float(value), vmin, vmax))
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
    # 簡化 Popup，只要有抓到相關名字就秀出來
    html = "<table style='font-size:12px'>"
    for k, v in properties.items():
        if k not in ["geometry", "_color"] and v is not None and str(v).strip() not in ["nan", "None", ""]:
            html += f"<tr><th style='text-align:left;padding:2px 8px 2px 0'>{k}</th><td style='text-align:right;padding:2px 0'>{_format_value(v)}</td></tr>"
    html += "</table>"
    return html

def create_leafmap_widget(
    lat_state, 
    lon_state, 
    target_district=None, 
    target_building_age=None, # 🌟 接收屋齡
    target_parking=None, 
    target_elevator=None,
    target_management=None
):
    import leafmap
    from ipyleaflet import GeoJSON, Marker, Popup
    from ipywidgets import HTML

    data, _vmin, _vmax = map_geojson()
    
    features = data.get("features", [])
    filtered_features = []
    
    for f in features:
        props = f.get("properties", {})
        keep = True
        
        # 1. 判斷行政區
        town_name = props.get("鄉鎮市") or props.get("鄉鎮市區")
        if target_district is not None and target_district.value != "全部" and town_name != target_district.value:
            keep = False
            
        # 2. 判斷管理組織
        if target_management is not None and target_management.value != "不拘":
            mgmt_str = str(props.get("有無管理組織") or props.get("有無管")).strip()
            actual_mgmt = "無" if mgmt_str in ["無", "None", "nan", "NaN", ""] else "有"
            if actual_mgmt != target_management.value:
                keep = False
                
        # 3. 判斷電梯
        if target_elevator is not None and target_elevator.value != "不拘":
            elev_str = str(props.get("電梯")).strip()
            actual_elev = "無" if elev_str in ["無", "None", "nan", "NaN", ""] else "有"
            if actual_elev != target_elevator.value:
                keep = False
        
        # 4. 判斷車位 (有字串代表有車位，空值代表無)
        if target_parking is not None and target_parking.value != "不拘":
            park_str = str(props.get("車位類別") or props.get("車位類")).strip()
            actual_park = "無" if park_str in ["無", "None", "nan", "NaN", ""] else "有"
            if actual_park != target_parking.value:
                keep = False

        # 5. 判斷屋齡 (假設今年是民國 114 年 / 2025)
        # 如果滑桿拉到 60 (最大值)，代表「不限屋齡」，就不作過濾
        if target_building_age is not None and target_building_age.value < 60:
            built_date = props.get("建築完成年月") or props.get("建築完")
            if built_date is not None and str(built_date).strip() not in ["None", "nan", "", "NaN"]:
                try:
                    built_num = float(built_date)
                    built_year = int(built_num // 10000) # 從 890512 提取出 89
                    age = 114 - built_year 
                    if age > target_building_age.value:
                        keep = False
                except:
                    keep = False # 資料怪怪的就濾掉
            else:
                keep = False # 沒有屋齡資料的也先隱藏

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