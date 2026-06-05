from __future__ import annotations

import html
import pandas as pd
import solara
import solara.lab

from .map_view import MAP_CENTER, create_leafmap_widget
from .scm_view import SCMPage  # 🌟 新增這一行：匯入 SCM 頁面模組

target_lat = solara.reactive(float(MAP_CENTER[0]))
target_lon = solara.reactive(float(MAP_CENTER[1]))
selected_tab = solara.reactive(0)

APP_CSS = """
/* 這裡保留老師原本的 CSS 樣式，只修改部分顏色或文字樣式，不影響排版 */
:root {
  --ds-ink: #16324f;
  --ds-ink-soft: #385169;
  --ds-green: #0f766e;
  --ds-green-dark: #14532d;
  --ds-rent: #b91c1c;
  --ds-rent-soft: #fee2e2;
  --ds-paper: #f7faf8;
  --ds-line: #dbe4df;
  --ds-line-strong: #b7c8c0;
}
.codex-app-page { width: 100%; box-sizing: border-box; padding: 22px 28px 30px 28px; background: linear-gradient(180deg, #f7faf8 0%, #ffffff 58%); }
.app-panel { border: 1px solid var(--ds-line); border-radius: 8px; background: rgba(255, 255, 255, 0.96); box-shadow: 0 10px 28px rgba(20, 83, 45, 0.06); box-sizing: border-box; width: 100%; overflow: hidden; }
.panel-body { padding: 16px 18px; }
.panel-kicker { color: var(--ds-green); font-size: 12px; font-weight: 700; letter-spacing: 0; margin-bottom: 6px; }
.panel-title { color: var(--ds-ink); font-size: 22px; line-height: 1.25; font-weight: 800; margin: 0 0 10px 0; }
.panel-title.small { font-size: 18px; margin-bottom: 6px; }
.panel-subtitle, .panel-copy { color: var(--ds-ink-soft); font-size: 14px; line-height: 1.7; margin: 0; }
.home-grid { display: grid; grid-template-columns: minmax(620px, 1.08fr) minmax(620px, 1fr); gap: 18px; align-items: stretch; width: 100%; }
.home-stack { display: grid; gap: 18px; }
.metric-grid { display: grid; grid-template-columns: repeat(4, minmax(118px, 1fr)); gap: 12px; margin-top: 10px; }
.metric-tile { border: 1px solid var(--ds-line); border-radius: 8px; padding: 13px 14px; background: linear-gradient(180deg, #ffffff 0%, #f8fbfa 100%); min-height: 78px; }
.metric-label { color: #607085; font-size: 12px; font-weight: 700; margin-bottom: 5px; }
.metric-value { color: var(--ds-ink); font-size: 26px; line-height: 1.1; font-weight: 850; }
.metric-tile:first-child .metric-value { color: var(--ds-rent); }
.app-table-wrap { overflow: auto; padding-right: 4px; }
.app-table { width: 100%; border-collapse: collapse; font-size: 13px; line-height: 1.45; }
.app-table th { position: sticky; top: 0; z-index: 1; background: #eef6f3; color: #123044; border-bottom: 1px solid var(--ds-line-strong); padding: 8px 9px; text-align: left; white-space: nowrap; }
.app-table td { border-bottom: 1px solid #edf2ef; padding: 7px 9px; vertical-align: top; }
.app-table tbody tr:nth-child(even) { background: #f8fbfa; }
.app-table tbody tr:hover { background: #fff1f1; }
.map-page { padding: 14px 18px 18px 18px; }
.map-shell { border: 1px solid var(--ds-line); border-radius: 8px; overflow: hidden; background: #ffffff; box-shadow: 0 10px 28px rgba(20, 83, 45, 0.06); position: relative; }
.map-badge { position: absolute; top: 14px; left: 62px; z-index: 500; max-width: min(420px, calc(100% - 76px)); border: 1px solid rgba(183, 200, 192, 0.9); border-left: 5px solid var(--ds-rent); border-radius: 8px; background: rgba(255, 255, 255, 0.94); box-shadow: 0 10px 24px rgba(22, 50, 79, 0.12); padding: 10px 12px 11px 12px; pointer-events: none; }
.map-badge-title { color: var(--ds-ink); font-size: 16px; font-weight: 850; line-height: 1.25; }
.map-badge-copy { color: var(--ds-ink-soft); display: block; font-size: 12px; line-height: 1.45; margin-top: 4px; }
.control-shell { border: 1px solid var(--ds-line); border-top: 4px solid var(--ds-green); border-radius: 8px; background: rgba(255, 255, 255, 0.97); box-shadow: 0 10px 28px rgba(20, 83, 45, 0.06); padding: 16px 18px 18px 18px; box-sizing: border-box; }
.control-hero { padding-bottom: 12px; }
.control-hero-title { color: var(--ds-ink); font-size: 20px; line-height: 1.25; font-weight: 850; margin: 0 0 8px 0; }
.control-section { border-top: 1px solid #edf2ef; padding-top: 12px; margin-top: 12px; }
.section-label { color: var(--ds-ink); font-size: 15px; font-weight: 800; margin-bottom: 8px; }
.coordinate-pill { color: var(--ds-green-dark); background: #ecfdf5; border: 1px solid #bbf7d0; border-radius: 999px; display: inline-block; font-size: 13px; font-weight: 700; padding: 5px 10px; }
.result-card { border: 1px solid #fecaca; border-left: 5px solid var(--ds-rent); border-radius: 8px; background: #fff7f7; padding: 12px 14px; margin-top: 14px; }
.result-value { color: var(--ds-rent); font-size: 26px; font-weight: 850; line-height: 1.15; }
@media (max-width: 1360px) { .home-grid { grid-template-columns: 1fr; } .metric-grid { grid-template-columns: repeat(2, minmax(140px, 1fr)); } }
@media (max-width: 1180px) { .map-page { flex-direction: column !important; overflow: visible !important; } .map-column, .control-column { flex: 1 1 auto !important; min-width: 0 !important; max-width: none !important; width: 100% !important; } .control-column { max-height: none !important; overflow-y: visible !important; } }
"""

def _home_html() -> str:
    intro = (
        "<section class='app-panel'><div class='panel-body'>"
        "<div class='panel-kicker'>TAOYUAN HOUSE PRICE EXPLORER</div>"
        "<h1 class='panel-title'>桃園市 2025 房屋買賣現況 WebApp</h1>"
        "<p class='panel-copy'>本系統展示桃園市房屋買賣實價登錄資料，"
        "目前提供地圖點位探索，未來將串接機器學習模型進行總價預測。</p>"
        "</div></section>"
    )
    return f"<div class='codex-app-page'><div class='home-grid'>{intro}</div></div>"

@solara.component
def HomePage():
    solara.HTML(tag="div", unsafe_innerHTML=_home_html())

@solara.component
def MapPanel():
    with solara.Column(classes=["map-shell"], style={"width": "100%"}):
        map_widget = solara.use_memo(lambda: create_leafmap_widget(target_lat, target_lon), [])
        solara.display(map_widget)
        solara.HTML(
            tag="div",
            unsafe_innerHTML=(
                "<div class='map-badge'><div class='panel-kicker'>INTERACTIVE MAP</div>"
                "<div class='map-badge-title'>房屋點位與目標位置</div>"
                f"<span class='map-badge-copy'>目前目標座標：{target_lon.value:.6f}, {target_lat.value:.6f}</span></div>"
            ),
        )

@solara.component
def ControlPanel():
    # 這裡就是你專屬的桃園房價控制變數
    district = solara.use_reactive("桃園區")
    building_age = solara.use_reactive(5)
    has_parking = solara.use_reactive("有")
    has_elevator = solara.use_reactive("有")
    has_balcony = solara.use_reactive("有")
    has_management = solara.use_reactive("有")
    
    test_msg = solara.use_reactive("")

    with solara.Column(classes=["control-shell"], style={"width": "100%"}):
        solara.HTML(
            tag="div",
            unsafe_innerHTML=(
                "<div class='control-hero'><div class='panel-kicker'>HOUSE PRICE EXPLORER</div>"
                "<h2 class='control-hero-title'>設定房屋屬性條件</h2>"
                "<p class='panel-copy'>在左側地圖點選或拖曳目標位置，並在下方設定房屋屬性條件。未來將可直接預測該區段的房價。</p>"
                f"<span class='coordinate-pill' style='margin-top:10px'>目標座標：{target_lon.value:.6f}, {target_lat.value:.6f}</span></div>"
            ),
        )

        with solara.Column(classes=["control-section"]):
            solara.HTML(tag="div", unsafe_innerHTML="<div class='section-label'>數值條件</div>")
            solara.SliderInt("屋齡 (年)", value=building_age, min=0, max=60)

        with solara.Column(classes=["control-section"]):
            solara.HTML(tag="div", unsafe_innerHTML="<div class='section-label'>類別條件</div>")
            
            solara.Select("行政區", 
                values=["桃園區", "中壢區", "八德區", "平鎮區", "龜山區", "蘆竹區", "大園區", "龍潭區", "楊梅區", "大溪區", "新屋區", "觀音區", "復興區"], 
                value=district)
            
            with solara.Row(gap="12px", style={"width": "100%"}):
                with solara.Column(style={"flex": "1 1 0"}):
                    solara.Select("車位", values=["無", "有"], value=has_parking)
                with solara.Column(style={"flex": "1 1 0"}):
                    solara.Select("電梯", values=["無", "有"], value=has_elevator)
                    
            with solara.Row(gap="12px", style={"width": "100%"}):
                with solara.Column(style={"flex": "1 1 0"}):
                    solara.Select("陽台", values=["無", "有"], value=has_balcony)
                with solara.Column(style={"flex": "1 1 0"}):
                    solara.Select("管理組織", values=["無", "有"], value=has_management)

        def dummy_prediction():
            test_msg.value = "介面改裝成功！目前為純展示模式（機器學習模型尚未切換至桃園資料）。"

        solara.Button("模擬預測", on_click=dummy_prediction, color="primary", outlined=False)

        if test_msg.value:
            solara.Success(test_msg.value)


@solara.component
def PredictionPage():
    with solara.Row(
        gap="18px",
        classes=["codex-app-page", "map-page"],
        style={
            "align-items": "stretch",
            "width": "100%",
            "min-height": "calc(100vh - 96px)",
            "overflow": "hidden",
        },
    ):
        with solara.Column(classes=["map-column"], style={"flex": "1 1 auto", "min-width": "640px"}):
            MapPanel()
        with solara.Column(
            classes=["control-column"],
            style={
                "flex": "0 0 560px",
                "min-width": "500px",
                "max-width": "620px",
                "max-height": "calc(100vh - 96px)",
                "overflow-y": "auto",
            },
        ):
            # 移除了 bundle 和 cache 的傳遞，純粹展示 UI
            ControlPanel()


@solara.component
def Page():
    solara.Title("桃園市房價展示 WebApp")
    solara.HTML(tag="style", unsafe_innerHTML=APP_CSS)
    
    with solara.lab.Tabs(value=selected_tab, grow=True, color="#0f766e", slider_color="#b91c1c"):
        solara.lab.Tab("首頁")
        solara.lab.Tab("地圖與分析")
        solara.lab.Tab("因果推論 (合成控制法)")  # 🌟 新增這一行：第三個標籤頁
        
    # 🌟 修改這裡的判斷邏輯，加入 selected_tab.value == 2 的情況
    if selected_tab.value == 0:
        HomePage()
    elif selected_tab.value == 1:
        PredictionPage()
    elif selected_tab.value == 2:
        SCMPage()