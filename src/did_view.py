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
    csv_path = APP_ROOT / "did_trend.csv"
    if csv_path.exists():
        df = pd.read_csv(csv_path)
        # 排除 2011、2012 這兩年資料筆數太少造成的極端值，從 2013 開始畫會比較穩健
        return df[df['year'] >= 2013], True
    return pd.DataFrame(), False

def get_did_table_data():
    csv_path = APP_ROOT / "did_table.csv"
    if csv_path.exists():
        df = pd.read_csv(csv_path)
        # 幫同學補上匯出時漏掉的模型名稱
        df.insert(0, '分析模型', ['傳統 OLS (聚合資料)', 'PanelOLS (TWFE 雙向固定效應)'])
        # 數字美化
        df['ATT 估計量（did 係數）'] = df['ATT 估計量（did 係數）'].round(2)
        df['標準誤'] = df['標準誤'].round(2)
        df['p-value'] = df['p-value'].round(4)
        return df, True
    return pd.DataFrame(), False

def get_did_event_data():
    csv_path = APP_ROOT / "did_event.csv"
    if csv_path.exists():
        return pd.read_csv(csv_path), True
    return pd.DataFrame(), False

@solara.component
def DIDPage():
    # 讀取真實資料
    df_trend, is_real_trend = get_did_trend_data()
    df_table, is_real_table = get_did_table_data()
    df_event, is_real_event = get_did_event_data()

    with solara.Column(classes=["codex-app-page"], style={"min-height": "100vh"}):
        
        # ─── 頂部標題區 ───
        solara.HTML(tag="div", unsafe_innerHTML=(
            "<div class='control-hero'>"
            "<div class='panel-kicker'>CAUSAL INFERENCE</div>"
            "<h1 class='control-hero-title'>政策效益評估：雙重差分法 (DID)</h1>"
            "<p class='panel-copy'>本頁面利用雙重差分法與雙向固定效應模型 (TWFE)，評估「桃園捷運開通」(以 2018 年為政策切點) 對沿線行政區房價的淨效應。模型嚴格控制了區域固有特性與時間共同趨勢，以捕捉最真實的因果關係。</p>"
            "</div>"
        ))

        if not is_real_trend or not is_real_table or not is_real_event:
            solara.Warning("💡 等待載入真實資料中...")
        else:
            solara.Success("✅ 已成功載入真實桃園捷運 DID 分析數據！")

        # ─── 核心區塊 1：平行趨勢與動態效應 (Event Study) ───
        with solara.Row(gap="20px", style={"margin-top": "20px", "align-items": "stretch"}):
            
            # 左側：平行趨勢圖
            with solara.Column(style={"flex": "1", "background": "white", "padding": "25px", "border-radius": "8px", "box-shadow": "0 4px 6px rgba(0,0,0,0.05)"}):
                solara.Markdown("### 📈 平行趨勢檢定 (Parallel Trends)")
                
                fig1, ax1 = plt.subplots(figsize=(8, 5))
                
                treat_data = df_trend[df_trend['region_treat'] == 1]
                control_data = df_trend[df_trend['region_treat'] == 0]
                
                ax1.plot(treat_data['year'], treat_data['unit_price_per_sqm'], marker='o', label='處理組 (捷運沿線)', color='#b91c1c', linewidth=2.5)
                ax1.plot(control_data['year'], control_data['unit_price_per_sqm'], marker='s', label='控制組 (其他區域)', color='#0f766e', linewidth=2.5)
                
                intervention_year = 2018
                ax1.axvline(x=intervention_year, color='grey', linestyle='--', linewidth=2, label=f'捷運綠線動工 ({intervention_year})')
                
                ax1.set_ylabel("平均每平方公尺單價 (元)")
                ax1.set_xticks(df_trend['year'].unique())
                ax1.grid(True, linestyle='--', alpha=0.5)
                ax1.spines['top'].set_visible(False)
                ax1.spines['right'].set_visible(False)
                ax1.legend()
                
                solara.FigureMatplotlib(fig1)

            # 右側：事件研究法 (動態效應圖)
            with solara.Column(style={"flex": "1", "background": "white", "padding": "25px", "border-radius": "8px", "box-shadow": "0 4px 6px rgba(0,0,0,0.05)"}):
                solara.Markdown("### 🎯 動態效應檢定 (Event Study)")
                
                fig2, ax2 = plt.subplots(figsize=(8, 5))
                
                # 計算誤差線的長度 (Y error = 上限-估計值, 估計值-下限)
                # 注意：如果 coef 是極小的數值 (例如 4.16e-11，代表基準年被設定為 0)
                y_err_lower = df_event['coef'] - df_event['lower_ci']
                y_err_upper = df_event['upper_ci'] - df_event['coef']
                
                ax2.errorbar(df_event['relative_year'], df_event['coef'], 
                             yerr=[y_err_lower, y_err_upper], 
                             fmt='o', color='#16324f', ecolor='#385169', elinewidth=2, capsize=4, markersize=6)
                
                # 畫一條 0 的水平基準線
                ax2.axhline(y=0, color='#b91c1c', linestyle='-', alpha=0.5)
                # 政策發生的基準年 (通常是 relative_year = 0 的前一年)
                ax2.axvline(x=-1, color='grey', linestyle='--', alpha=0.5)
                
                ax2.set_ylabel("DID 估計係數 (淨效應)")
                ax2.set_xlabel("政策相對年份 (0 = 2018年)")
                ax2.grid(True, linestyle='--', alpha=0.4)
                ax2.spines['top'].set_visible(False)
                ax2.spines['right'].set_visible(False)
                
                solara.FigureMatplotlib(fig2)

        # ─── 核心區塊 2：迴歸結果表與結論 ───
        with solara.Row(gap="20px", style={"margin-top": "20px", "align-items": "stretch"}):
            with solara.Column(style={"flex": "1", "background": "white", "padding": "25px", "border-radius": "8px", "box-shadow": "0 4px 6px rgba(0,0,0,0.05)"}):
                solara.Markdown("### 📊 政策處理效應 (ATT) 估計結果")
                
                solara.DataFrame(df_table)
                
                solara.HTML(tag="div", unsafe_innerHTML=(
                    "<div style='margin-top: 20px; padding: 15px; background-color: #f8fafc; border-left: 4px solid #0f766e; border-radius: 4px;'>"
                    "<h4 style='margin-top: 0; color: #0f766e;'>💡 深度結論剖析</h4>"
                    "<p style='font-size: 14px; margin-bottom: 0; line-height: 1.6;'>"
                    "<b>1. 動態效應觀察：</b> 從上方的 Event Study 可以看出，政策前 (相對年份 < 0) 的係數上下波動且信賴區間包含 0，代表政策前沒有顯著的預期效應，符合平行趨勢假設。<br><br>"
                    "<b>2. 迴歸結果解讀：</b> PanelOLS 模型顯示，捷運開通為處理組帶來了每平方公尺約 <strong>2,769 元</strong> 的正向溢價，但其 <strong>p-value (0.598) 遠大於 0.05</strong>，統計上不顯著。<br><br>"
                    "<b>3. 綜合結論：</b> 這與我們在 SCM 模型中看到的結果不謀而合。這表示在控制了地區固定特性與時間趨勢後，桃園捷運沿線的房價並沒有因為動工而出現「異常暴漲」。此結果打破了傳統『軌道經濟學必漲』的迷思，可能歸因於捷運紅利的提早反映、施工期的黑暗期抗性，或是資金外溢至鄰近的非捷運區域。"
                    "</p></div>"
                ))