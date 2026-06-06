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
    """讀取真實 SCM 趨勢資料"""
    csv_path = APP_ROOT / "scm_trend.csv"
    if csv_path.exists():
        df = pd.read_csv(csv_path)
        return df, True
    
    # --- 萬一沒抓到檔案的防呆假資料 ---
    years = np.arange(2013, 2026)
    synthetic = 55 + 2 * (years - 2013) + np.random.normal(0, 2, len(years))
    actual = synthetic.copy()
    actual[years >= 2018] += 5 * (years[years >= 2018] - 2017) 
    df = pd.DataFrame({'Year': years, 'Actual': actual, 'Synthetic': synthetic})
    return df, False

def get_weights_data():
    """讀取真實 SCM 權重資料並美化表格"""
    csv_path = APP_ROOT / "scm_weights.csv"
    if csv_path.exists():
        df = pd.read_csv(csv_path)
        # 1. 將 pandas 預設的 Unnamed: 0 改名為行政區
        if 'Unnamed: 0' in df.columns:
            df = df.rename(columns={'Unnamed: 0': '鄉鎮市區'})
        
        # 2. 將極小的科學記號權重 (如 6e-08) 設為 0，並四捨五入到小數點後 4 位
        df['Weight'] = df['Weight'].apply(lambda x: round(x, 4) if x > 0.0001 else 0)
        
        # 3. (選用) 只顯示權重 > 0 的區域，讓表格更簡潔專注
        df = df[df['Weight'] > 0].sort_values('Weight', ascending=False).reset_index(drop=True)
        return df, True
    
    # --- 防呆假權重 ---
    df = pd.DataFrame({
        '鄉鎮市區': ['平鎮區', '中壢區', '新屋區'],
        'Weight': [0.5502, 0.4230, 0.0268]
    })
    return df, False

@solara.component
def SCMPage():
    # 讀取資料
    df_trend, is_real_trend = get_trend_data()
    df_weights, is_real_weights = get_weights_data()

    with solara.Column(classes=["codex-app-page"], style={"min-height": "100vh"}):
        
        # 標題區塊
        solara.HTML(tag="div", unsafe_innerHTML=(
            "<div class='control-hero'>"
            "<div class='panel-kicker'>CAUSAL INFERENCE</div>"
            "<h1 class='control-hero-title'>政策效益評估：合成控制法 (SCM)</h1>"
            "<p class='panel-copy'>本頁面利用合成控制法，為「捷運通過之行政區」尋找未受政策影響的區域組合，打造出一個「虛擬的對照組(Synthetic)」。藉此對比目標區域在 2018 年捷運通車前後的真實房價走勢與模擬走勢差異。</p>"
            "</div>"
        ))
        
        # 狀態提示
        if not is_real_trend or not is_real_weights:
            solara.Warning("💡 目前尚未偵測到真實的 CSV 資料檔，目前顯示的圖表為展示用數據。")
        else:
            solara.Success("✅ 已成功載入真實 SCM 分析數據！")

        with solara.Row(gap="20px", style={"margin-top": "20px", "align-items": "flex-start"}):
            # 左側：趨勢圖
            with solara.Column(style={"flex": "2", "background": "white", "padding": "20px", "border-radius": "8px", "box-shadow": "0 4px 6px rgba(0,0,0,0.05)"}):
                solara.Markdown("### 📈 實際與合成房價趨勢對比")
                
                fig, ax = plt.subplots(figsize=(10, 5))
                
                # 繪製真實的折線
                ax.plot(df_trend['Year'], df_trend['Actual'], marker='o', label='實際房價 (捷運沿線)', color='#b91c1c', linewidth=2.5)
                ax.plot(df_trend['Year'], df_trend['Synthetic'], marker='s', label='合成房價 (虛擬對照組)', color='#0f766e', linestyle='--', linewidth=2.5)
                
                # 標示政策介入年份 (捷運通車 2018)
                intervention_year = 2018
                ax.axvline(x=intervention_year, color='grey', linestyle=':', linewidth=2, label=f'捷運通車 ({intervention_year})')
                
                # 美化圖表
                ax.set_ylabel("房屋單價 (千元/平方公尺)", fontsize=12)
                ax.set_xticks(df_trend['Year'].unique())
                ax.grid(True, linestyle='--', alpha=0.6)
                ax.legend(loc='upper left')
                ax.spines['top'].set_visible(False)
                ax.spines['right'].set_visible(False)
                
                solara.FigureMatplotlib(fig)

            # 右側：權重表
            with solara.Column(style={"flex": "1", "background": "white", "padding": "20px", "border-radius": "8px", "box-shadow": "0 4px 6px rgba(0,0,0,0.05)"}):
                solara.Markdown("### 🧩 合成對照組權重配置")
                solara.Markdown("下表顯示演算法自動挑選出的「捐贈池 (Donor Pool)」最優權重比例。權重總和為 1。")
                
                # 顯示清理過的完美表格
                solara.DataFrame(df_weights)
                
                solara.HTML(tag="div", unsafe_innerHTML=(
                    "<div style='margin-top: 15px; padding: 15px; background-color: #f8fafc; border-left: 4px solid #0f766e; border-radius: 4px;'>"
                    "<h4 style='margin-top: 0; color: #0f766e;'>💡 權重解讀</h4>"
                    "<p style='font-size: 14px; margin-bottom: 0;'>模型判定 <strong>平鎮區</strong> 與 <strong>中壢區</strong> 的歷史房價走勢與結構，最能完美模擬捷運沿線區域的「反事實 (Counterfactual)」狀態。</p>"
                    "</div>"
                ))