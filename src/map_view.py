def create_leafmap_widget(
    lat_state, 
    lon_state, 
    # 加入從 UI 傳過來的篩選條件
    target_district=None, 
    target_parking=None, 
    target_elevator=None,
    target_management=None
):
    import leafmap
    from ipyleaflet import GeoJSON, Marker, Popup
    from ipywidgets import HTML

    # 1. 取得所有資料
    data, _vmin, _vmax = map_geojson()
    
    # 2. 如果有篩選條件，就在這裡過濾 GeoJSON features
    features = data.get("features", [])
    filtered_features = []
    
    for f in features:
        props = f.get("properties", {})
        keep = True
        
        # 行政區篩選
        if target_district and target_district.value != "全部" and props.get("鄉鎮市") != target_district.value:
            keep = False
            
        # 由於你的 CSV 中可能沒有直接對應的欄位，這裡先示範邏輯
        # 如果你的原始資料有對應欄位，例如 "有無管理組織"
        if target_management and target_management.value != "不拘":
            # 假設資料裡的值是 "有" 或 "無"
            if props.get("有無管理組織") != target_management.value:
                keep = False
                
        # (你可以依此類推，加入車位、電梯的篩選邏輯，前提是資料要先被 load_map_gdf 讀進來)
        
        if keep:
            filtered_features.append(f)
            
    # 將過濾後的特徵重新包裝回 GeoJSON 格式
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

    # 3. 使用過濾後的 filtered_data 畫圖
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