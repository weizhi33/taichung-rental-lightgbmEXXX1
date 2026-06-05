import solara
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# 設定字體，避免圖表上的中文字變成方塊
plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'Taipei Sans TC Beta', 'Arial Unicode MS', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

APP_ROOT = Path(__file__).resolve().parents[1]

def get_did_trend_data():
    """讀取趨勢資料，若無 CSV 則生成模擬桃園捷運的假資料"""
    csv_path = APP_ROOT / "did_trend.csv"
    if csv_path.exists():
        return pd.read_csv(csv_path), True
    
    # 建立完美的假資料 (模擬 2013-2025，2018年為政策切點)
    years = list(range(2013, 2026)) * 2
    treat = [0]*13 + [1]*13  # 0=控制組, 1=處理組
    np.random.seed(42)
    price = []
    
    for y, t in zip(years, treat):
        # 基礎房價隨年份緩步上漲
        base = 50000 + (y - 2013) * 1500
        if t == 1:
            # 處理組 (捷運沿線) 原本價格就稍微高一點
            base += 12000  
            # 2018 年通車後，處理組再額外疊加一點漲幅 (模擬 DID 效應)
            if y >= 2018:
                base += 2500
        # 加上一點隨機波動讓圖看起來更真實
        price.append(base + np.random.normal(0, 1500))
        
    df_mock = pd.DataFrame({'year': years, 'region_treat': treat, 'unit_price_per_sqm': price})
    return df_mock, False

def get_did_table_data():
    """讀取 DID 迴歸結果表，若無 CSV 則生成假資料"""
    csv_path = APP_ROOT / "did_table.csv"
    if csv_path.exists():
        return pd.read_csv(csv_path), True
    
    # 建立假資料 (模擬你們筆記本裡的真實分析結果)
    df_mock = pd.DataFrame({
        '分析模型': ['傳統 OLS (聚合資料)', 'PanelOLS (TWFE 雙向固定效應)'],
        'ATT 估計量 (元/平方公尺)': [-1275.76, 2768.99],
        '標準誤 (Robust SE)': [5868.11, 5239.23],
        'P-value': [0.828, 0.598]
    })
    return df_mock, False

@solara.component
def DIDPage():
    # 抓取資料
    df_trend, is_real_trend = get_did_trend_data()
    df_table, is_real_table = get_did_table_data()

    with solara.Column(classes=["codex-app-page"], style={"min-height": "100vh"}):
        
        # ─── 標題與說明區塊 ───
        solara.HTML(tag="div", unsafe_innerHTML=(
            "<div class='control-hero'>"
            "<div class='panel-kicker'>CAUSAL INFERENCE</div>"
            "<h1 class='control-hero-title'>政策效益評估：雙重差分法 (DID)</h1>"
            "<p class='panel-copy'>本頁面利用雙重差分法與雙向固定效應模型 (TWFE)，評估「桃園捷運開通」(以 2018 年為政策切點) 對沿線行政區房價的淨效應。模型控制了區域固有特性與時間共同趨勢，以捕捉最真實的因果關係。</p>"
            "</div>"
        ))

        # ─── 狀態提示橫幅 ───
        if not is_real_trend or not is_real_table:
            solara.Warning("💡 目前為「UI 展示模式」：尚未偵測到真實的 `did_trend.csv` 與 `did_table.csv`，圖表使用預設模擬趨勢，表格為筆記本暫存數據。上傳檔案後將自動切換。")
        else:
            solara.Success("✅ 已成功載入真實 DID 分析數據！")

        # ─── 圖表與表格區塊 ───
        with solara.Row(gap="20px", style={"margin-top": "20px", "align-items": "flex-start"}):
            
            # 左側：平行趨勢圖
            with solara.Column(style={"flex": "1.2", "background": "white", "padding": "20px", "border-radius": "8px", "box-shadow": "0 4px 6px rgba(0,0,0,0.05)"}):
                solara.Markdown("### 📈 平行趨勢檢定 (Parallel Trends)")
                solara.Markdown("觀察 2018 年捷運通車前，處理組 (捷運沿線) 與控制組 (其他區域) 是否具備平行的房價成長趨勢。")
                
                fig, ax = plt.subplots(figsize=(8, 5))
                
                # 分離處理組與控制組
                treat_data = df_trend[df_trend['region_treat'] == 1]
                control_data = df_trend[df_trend['region_treat'] == 0]
                
                # 繪製折線
                ax.plot(treat_data['year'], treat_data['unit_price_per_sqm'], marker='o', label='處理組 (捷運沿線)', color='#b91c1c', linewidth=2.5)
                ax.plot(control_data['year'], control_data['unit_price_per_sqm'], marker='s', label='控制組 (其他區域)', color='#0f766e', linewidth=2.5)
                
                # 畫上政策介入的垂直虛線
                intervention_year = 2018
                ax.axvline(x=intervention_year, color='grey', linestyle='--', linewidth=2, label=f'捷運通車 ({intervention_year})')
                
                # 圖表美化設定
                ax.set_ylabel("平均每平方公尺單價 (元)")
                ax.set_xticks(df_trend['year'].unique())
                ax.grid(True, linestyle='--', alpha=0.5)
                ax.spines['top'].set_visible(False)
                ax.spines['right'].set_visible(False)
                ax.legend()
                
                # 將圖表顯示在網頁上
                solara.FigureMatplotlib(fig)

            # 右側：迴歸結果與結論
            with solara.Column(style={"flex": "1", "background": "white", "padding": "20px", "border-radius": "8px", "box-shadow": "0 4px 6px rgba(0,0,0,0.05)"}):
                solara.Markdown("### 📊 政策處理效應 (ATT) 估計結果")
                solara.Markdown("比較傳統 OLS 與 **PanelOLS (TWFE)** 模型估計的 `did` 係數 (政策淨效應)。")
                
                # 顯示資料表
                solara.DataFrame(df_table)
                
                # 結論方塊
                solara.HTML(tag="div", unsafe_innerHTML=(
                    "<div style='margin-top: 20px; padding: 15px; background-color: #f8fafc; border-left: 4px solid #0f766e; border-radius: 4px;'>"
                    "<h4 style='margin-top: 0; color: #0f766e;'>💡 分析結論</h4>"
                    "<p style='font-size: 14px; margin-bottom: 0; line-height: 1.6;'>"
                    "PanelOLS 模型顯示，捷運開通為處理組帶來每平方公尺約 <strong>2,769 元</strong> 的溢價。然而，其 <strong>P-value (0.598) 遠大於 0.05</strong>，在統計上並不顯著。<br><br>"
                    "這代表在嚴格控制了「地區不變特性」與「全域年份趨勢」後，我們<strong>無法證實桃園捷運的開通對沿線房價有異常的推升作用</strong>。這可能是因為市場預期心理提早發酵，利多早已反映在通車前的房價中，或是受總體經濟與大環境房市波動所掩蓋。"
                    "</p></div>"
                ))