import solara
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import urllib.request
import os
import matplotlib
from pathlib import Path

# ─── 🌟 雲端伺服器中文字型自動下載註冊機制 ───
APP_ROOT = Path(__file__).resolve().parents[1]
FONT_FILE = APP_ROOT / "NotoSansTC-Regular.ttf"

if not FONT_FILE.exists():
    try:
        font_url = "https://github.com/google/fonts/raw/main/ofl/notosanstc/NotoSansTC%5Bwght%5D.ttf"
        urllib.request.urlretrieve(font_url, FONT_FILE)
    except Exception as e:
        pass

if FONT_FILE.exists():
    try:
        matplotlib.font_manager.fontManager.addfont(str(FONT_FILE))
        matplotlib.rc('font', family='Noto Sans TC')
    except Exception as e:
        pass

plt.rcParams['font.sans-serif'] = ['Noto Sans TC', 'WenQuanYi Micro Hei', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False
# ───────────────────────────────────────────────────

def get_did_trend_data():
    """讀取真實 DID 趨勢資料"""
    csv_path = APP_ROOT / "did_trend.csv"
    if csv_path.exists():
        df = pd.read_csv(csv_path)
        # 排除 2011、2012 資料筆數過少造成的異常值，專注於 2013 年後的穩定趨勢
        return df[df['year'] >= 2013], True
    return pd.DataFrame(), False

def get_did_table_data():
    """讀取 DID 迴歸結果表"""
    csv_path = APP_ROOT / "did_table.csv"
    if csv_path.exists():
        df = pd.read_csv(csv_path)
        if '分析模型' not in df.columns:
            df.insert(0, '分析模型', ['傳統 OLS (區域聚合)', 'PanelOLS (TWFE 雙向固定效應)'])
        df['ATT 估計量（did 係數）'] = df['ATT 估計量（did 係數）'].round(2)
        df['標準誤'] = df['標準誤'].round(2)
        df['p-value'] = df['p-value'].round(4)
        return df, True
    return pd.DataFrame(), False

def get_did_event_data():
    """讀取動態效應資料"""
    csv_path = APP_ROOT / "did_event.csv"
    if csv_path.exists():
        return pd.read_csv(csv_path), True
    return pd.DataFrame(), False

@solara.component
def DIDPage():
    df_trend, is_real_trend = get_did_trend_data()
    df_table, is_real_table = get_did_table_data()
    df_event, is_real_event = get_did_event_data()

    with solara.Column(classes=["codex-app-page"], style={"min-height": "100vh"}):
        
        # ─── 頂部標題區 ───
        solara.HTML(tag="div", unsafe_innerHTML=(
            "<div class='control-hero'>"
            "<div class='panel-kicker'>CAUSAL INFERENCE</div>"
            "<h1 class='control-hero-title'>政策效益評估：雙重差分法 (DID)</h1>"
            "<p class='panel-copy'>本頁面展示雙重差分法 (Difference-in-Differences) 模型與時間固定效應 (TWFE) 的檢定結果。我們透過檢驗統計上的顯著性與平行趨勢假設，客觀評估捷運綠線動工對區域房價的因果推論效力。</p>"
            "</div>"
        ))

        if not is_real_trend or not is_real_table or not is_real_event:
            solara.Warning("💡 等待載入真實資料中...")
        else:
            solara.Success("✅ 已成功載入真實桃園捷運 DID 分析數據與完整計量檢定結果！")

        # ─── 第一核心區塊：平行趨勢與動態效應圖 ───
        with solara.Row(gap="20px", style={"margin-top": "20px", "align-items": "stretch"}):
            
            # 左側：原始聚合趨勢圖
            with solara.Column(style={"flex": "1", "background": "white", "padding": "25px", "border-radius": "8px", "box-shadow": "0 4px 6px rgba(0,0,0,0.05)"}):
                solara.Markdown("### 📈 雙重差分原始時間趨勢")
                solara.Markdown("比較處理組（捷運沿線行政區）與控制組（其他行政區）在 2018 年動工前後的平均單價走勢：")
                
                if is_real_trend:
                    fig1, ax1 = plt.subplots(figsize=(8, 5))
                    treat_data = df_trend[df_trend['region_treat'] == 1]
                    control_data = df_trend[df_trend['region_treat'] == 0]
                    
                    ax1.plot(treat_data['year'], treat_data['unit_price_per_sqm'], marker='o', label='處理組 (捷運沿線)', color='#b91c1c', linewidth=2.5)
                    ax1.plot(control_data['year'], control_data['unit_price_per_sqm'], marker='s', label='控制組 (其他區域)', color='#0f766e', linewidth=2.5)
                    
                    ax1.axvline(x=2018, color='#475569', linestyle='--', linewidth=2, label='捷運綠線動工 (2018)')
                    ax1.set_ylabel("平均每平方公尺單價 (元)", fontsize=11)
                    ax1.set_xticks(df_trend['year'].unique())
                    ax1.grid(True, linestyle='--', alpha=0.5)
                    ax1.spines['top'].set_visible(False)
                    ax1.spines['right'].set_visible(False)
                    ax1.legend()
                    solara.FigureMatplotlib(fig1)

            # 右側：事件研究法 (動態效應圖)
            with solara.Column(style={"flex": "1", "background": "white", "padding": "25px", "border-radius": "8px", "box-shadow": "0 4px 6px rgba(0,0,0,0.05)"}):
                solara.Markdown("### 🎯 動態效應與事件研究法 (Event Study)")
                solara.Markdown("展示相對於基準年各年度政策效應的點估計值與 95% 信賴區間，用以嚴格檢定預期效應：")
                
                if is_real_event:
                    fig2, ax2 = plt.subplots(figsize=(8, 5))
                    
                    # 排除因為基準年設定導致區間寬度為 0 的微小數值雜訊
                    df_event_filtered = df_event[abs(df_event['upper_ci'] - df_event['lower_ci']) > 1e-4]
                    
                    y_err_lower = df_event_filtered['coef'] - df_event_filtered['lower_ci']
                    y_err_upper = df_event_filtered['upper_ci'] - df_event_filtered['coef']
                    
                    ax2.errorbar(df_event_filtered['relative_year'], df_event_filtered['coef'], 
                                 yerr=[y_err_lower, y_err_upper], 
                                 fmt='o-', color='#16324f', ecolor='#64748b', elinewidth=2, capsize=4, markersize=6, label='動態效應估計值')
                    
                    ax2.axhline(y=0, color='#b91c1c', linestyle='-', alpha=0.5)
                    ax2.axvline(x=0, color='#475569', linestyle=':', linewidth=2, label='動工基準年')
                    
                    ax2.set_ylabel("DID 估計係數", fontsize=11)
                    ax2.set_xlabel("政策相對年份 (0 代表 2018 年)", fontsize=11)
                    ax2.grid(True, linestyle='--', alpha=0.4)
                    ax2.spines['top'].set_visible(False)
                    ax2.spines['right'].set_visible(False)
                    ax2.legend(loc='lower left')
                    solara.FigureMatplotlib(fig2)

        # ─── 第二核心區塊：迴歸結果表與嚴謹診斷面版 ───
        with solara.Row(gap="20px", style={"margin-top": "20px", "align-items": "stretch"}):
            
            # 左下：迴歸結果表
            with solara.Column(style={"flex": "1", "background": "white", "padding": "25px", "border-radius": "8px", "box-shadow": "0 4px 6px rgba(0,0,0,0.05)"}):
                solara.Markdown("### 📊 政策處理效應 (ATT) 估計結果")
                solara.Markdown("展示對比區域聚合層級下，傳統普通最小平方法 (OLS) 與考慮雙向固定效應的 PanelOLS 估計數據：")
                
                if is_real_table:
                    solara.DataFrame(df_table)
                
                solara.HTML(tag="div", unsafe_innerHTML=(
                    "<div style='margin-top: 18px; padding: 15px; background-color: #f8fafc; border-left: 4px solid #475569; border-radius: 4px;'>"
                    "<h4 style='margin-top: 0; color: #1e293b; font-size: 14.5px;'>📊 估計效應簡評</h4>"
                    "<p style='font-size: 13px; margin-bottom: 0; line-height: 1.5; color: #475569;'>"
                    "即使在納入雙向固定效應的 PanelOLS 模型下，`did` 交互項係數雖然為正值 (2,769.00)，但其 <b>p-value 達 0.5980</b>，在統計學上遠未達到顯著水準，意味著常規 DID 模型無法證實捷運興建對沿線房價有異常拉抬效應。"
                    "</p></div>"
                ))

            # 右下：深度診斷面板
            with solara.Column(style={"flex": "1.2", "background": "white", "padding": "25px", "border-radius": "8px", "box-shadow": "0 4px 6px rgba(0,0,0,0.05)"}):
                solara.Markdown("### 🎓 計量經濟學診斷：為什麼傳統 DID 失效？")
                
                solara.HTML(tag="div", unsafe_innerHTML=(
                    "<div style='display: grid; gap: 14px;'>"
                    
                    "  <div style='background-color: #fdf2f2; padding: 12px; border-radius: 6px; border: 1px solid #fde2e2;'>"
                    "    <b style='color: #991b1b; font-size: 14px;'>🚨 關鍵發現：平行趨勢假設被顯著拒絕</b>"
                    "    <p style='margin: 4px 0 0 0; font-size: 13px; color: #7f1d1d; line-height: 1.5;'>"
                    "    研究團隊進行了嚴格的政策前置期檢定：<br>"
                    "    1. <b>Granger 預期效應檢定：</b> 檢定結果之 <b>p-value = 0.0077</b>，強烈拒絕平行趨勢的虛無假設。<br>"
                    "    2. <b>前置期線性趨勢檢定：</b> 線性趨勢檢定同樣顯著拒絕 (p = 0.0460)。<br>"
                    "    這一致證實：在 2018 年捷運興建前，處理組與控制組的房價變動本就存在結構性發散。"
                    "    </p>"
                    "  </div>"
                    
                    "  <div style='border-left: 3px solid #16324f; padding-left: 12px;'>"
                    "    <b style='color: #16324f; font-size: 14px;'>🎯 預期效應 (Anticipation Effect) 的干擾</b>"
                    "    <p style='margin: 4px 0 0 0; font-size: 12.5px; color: #385169; line-height: 1.5;'>"
                    "    從動態效應圖 (Event Study) 可以清晰看見，在相對年份 -5 到 -2 期間（即動工前數年），處理組的房價就已出現顯著的震盪溢價。這高度證實了「預期效應」的存在──買盤與建商早在規劃、送審階段就已提早進場炒作，導致動工時（相對年份0）的基礎價格已被大幅墊高，壓縮了動工後的因果效應表現。"
                    "    </p>"
                    "  </div>"
                    
                    "  <div style='background-color: #f0fdf4; padding: 12px; border-radius: 6px; border: 1px solid #dcfce7;'>"
                    "    <b style='color: #166534; font-size: 13.5px;'>💡 本研究引入合成控制法 (SCM) 的學術動機</b>"
                    "    <p style='margin: 4px 0 0 0; font-size: 12.5px; color: #14532d; line-height: 1.5;'>"
                    "    由於傳統 DID 的控制組無法通過平行趨勢假設，若直接採用其估計出的 ATT 係數將會包含嚴重的選擇性偏誤。這完美確立了本專題引進<b>合成控制法 (SCM)</b> 的必要性──透過對非捷運行政區進行最優權重配置，重新合成一個能完美契合處理組前置期軌跡的反事實替身，從而獲得更具說服力的因果推論結果。"
                    "    </p>"
                    "  </div>"
                    
                    "</div>"
                ))