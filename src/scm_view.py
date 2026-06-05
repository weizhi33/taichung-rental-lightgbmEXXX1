import solara
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# 設定字體，避免圖表上的中文字變成方塊
plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'Taipei Sans TC Beta', 'Arial Unicode MS', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

APP_ROOT = Path(__file__).resolve().parents[1]

def get_trend_data():
    """如果找不到真實 CSV，就自動生成一份展示用的假資料"""
    csv_path = APP_ROOT / "scm_trend.csv"
    if csv_path.exists():
        return pd.read_csv(csv_path), True
    
    # --- 生成假資料 (Mock Data) ---
    years = np.arange(2013, 2026)
    # 假設政策在 2020 年發生，2020 之前兩者重合，之後實際房價飆漲
    synthetic = 150 + 5 * (years - 2013) + np.random.normal(0, 2, len(years))
    actual = synthetic.copy()
    actual[years >= 2020] += 15 * (years[years >= 2020] - 2019) 
    
    df = pd.DataFrame({'Year': years, 'Actual': actual, 'Synthetic': synthetic})
    return df, False

def get_weights_data():
    """如果找不到真實 CSV，就自動生成一份展示用的假權重"""
    csv_path = APP_ROOT / "scm_weights.csv"
    if csv_path.exists():
        return pd.read_csv(csv_path), True
    
    # --- 生成假權重 ---
    df = pd.DataFrame({
        '鄉鎮市區': ['中壢區', '龜山區', '平鎮區', '楊梅區', '其他'],
        'Weight': [0.452, 0.315, 0.158, 0.075, 0.000]
    })
    return df, False

@solara.component
def SCMPage():
    # 讀取資料 (會自動判斷要用真的還假的)
    df_trend, is_real_trend = get_trend_data()
    df_weights, is_real_weights = get_weights_data()

    with solara.Column(classes=["codex-app-page"], style={"min-height": "100vh"}):
        
        # 標題區塊
        solara.HTML(tag="div", unsafe_innerHTML=(
            "<div class='control-hero'>"
            "<div class='panel-kicker'>CAUSAL INFERENCE</div>"
            "<h1 class='control-hero-title'>政策效益評估：合成控制法 (SCM)</h1>"
            "<p class='panel-copy'>本頁面利用合成控制法，尋找未受政策影響的行政區組成「合成對照組」，藉此對比目標區域在政策介入前後的房價差異。</p>"
            "</div>"
        ))
        
        # 如果是假資料，顯示溫馨提示
        if not is_real_trend or not is_real_weights:
            solara.Warning("💡 目前為「UI 展示模式」：由於尚未偵測到真實的 CSV 資料檔，目前顯示的圖表為系統自動生成的模擬數據。請稍後上傳 `scm_trend.csv` 與 `scm_weights.csv`。")
        else:
            solara.Success("✅ 已成功載入真實 SCM 分析數據！")

        with solara.Row(gap="20px", style={"margin-top": "20px", "align-items": "flex-start"}):
            # 左側：趨勢圖
            with solara.Column(style={"flex": "2", "background": "white", "padding": "20px", "border-radius": "8px", "box-shadow": "0 4px 6px rgba(0,0,0,0.05)"}):
                solara.Markdown("### 📈 實際與合成房價趨勢對比")
                
                fig, ax = plt.subplots(figsize=(10, 5))
                
                # 繪製折線
                ax.plot(df_trend['Year'], df_trend['Actual'], label='實際房價 (Treated)', color='#b91c1c', linewidth=2.5)
                ax.plot(df_trend['Year'], df_trend['Synthetic'], label='合成房價 (Synthetic)', color='#0f766e', linestyle='--', linewidth=2.5)
                
                # 標示政策介入年份 (假設為 2020)
                intervention_year = 2020
                ax.axvline(x=intervention_year, color='grey', linestyle=':', linewidth=2, label=f'政策介入 ({intervention_year})')
                
                # 美化圖表
                ax.set_ylabel("房屋單價 (千元/平方公尺)", fontsize=12)
                ax.grid(True, linestyle='--', alpha=0.6)
                ax.legend(loc='upper left')
                ax.spines['top'].set_visible(False)
                ax.spines['right'].set_visible(False)
                
                solara.FigureMatplotlib(fig)

            # 右側：權重表
            with solara.Column(style={"flex": "1", "background": "white", "padding": "20px", "border-radius": "8px", "box-shadow": "0 4px 6px rgba(0,0,0,0.05)"}):
                solara.Markdown("### 🧩 合成對照組權重配置")
                solara.Markdown("下表顯示用來模擬目標區域的「捐贈池 (Donor Pool)」行政區權重比例：")
                solara.DataFrame(df_weights)