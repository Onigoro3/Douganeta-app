import streamlit as st
import google.generativeai as genai
import os
import json
import pandas as pd
import requests
import datetime
from dotenv import load_dotenv

# --- 設定の読み込み ---
load_dotenv()

# --- ページ設定 ---
st.set_page_config(page_title="Japan Video Planner", layout="wide", initial_sidebar_state="collapsed")

# ==========================================
# 🎨 デザイン調整 (スマホ2列 強制配置版)
# ==========================================
st.markdown("""
    <style>
    /* ヘッダー・フッター削除 */
    header[data-testid="stHeader"], footer {display: none !important;}
    
    /* 全体の余白調整 */
    .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 5rem !important;
        padding-left: 0.2rem !important;
        padding-right: 0.2rem !important;
    }

    /* ★スマホ (幅768px以下) の時のレイアウト制御★ */
    @media (max-width: 768px) {
        /* 横並びコンテナの設定: 隙間(gap)をゼロにするのが重要 */
        [data-testid="stHorizontalBlock"] {
            flex-wrap: wrap !important;
            gap: 0 !important; /* これがないと50%+50%で改行されてしまう */
            padding: 0 !important;
        }
        
        /* カラム（列）の設定: 幅をきっちり50%にする */
        div[data-testid="column"] {
            flex: 0 0 50% !important;
            width: 50% !important;
            max-width: 50% !important;
            min-width: 50% !important;
            padding: 2px !important; /* ボタン同士の隙間はここで作る */
            margin: 0 !important;
        }
        
        /* ボタンの文字サイズと高さ調整 */
        .stButton > button {
            font-size: 11px !important;
            padding: 2px 4px !important;
            min-height: 42px !important;
            height: 100% !important;
            line-height: 1.2 !important;
        }
    }

    /* --- PC・共通デザイン --- */
    
    /* ボタン共通デザイン */
    .stButton > button {
        width: 100% !important;
        border-radius: 8px !important;
        min-height: 3.5rem; /* PCでの高さ */
        height: auto;
        font-weight: bold !important;
        
        /* 色指定: 白背景・黒文字で見やすく */
        background-color: #ffffff !important;
        color: #262730 !important;
        border: 1px solid #d0d7de !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        transition: all 0.1s;
    }
    
    /* ボタンを押したときの反応 */
    .stButton > button:active, .stButton > button:focus:not(:active) {
        background-color: #FF4B4B !important;
        color: #ffffff !important;
        border-color: #FF4B4B !important;
        transform: scale(0.98);
    }
    .stButton > button:hover {
        border-color: #FF4B4B !important;
        color: #FF4B4B !important;
    }

    /* バケツ（選択タグ）のデザイン */
    .tag-container {
        background-color: #ffffff;
        padding: 8px;
        border-radius: 8px;
        margin-bottom: 10px;
        border: 2px solid #FF4B4B;
        text-align: center;
        min-height: 40px;
        color: #333;
    }
    
    .selected-tag {
        display: inline-block;
        background-color: #FF4B4B;
        color: white !important;
        padding: 4px 10px;
        margin: 3px;
        border-radius: 15px;
        font-size: 12px;
        font-weight: bold;
    }

    /* 太陽シミュレーションエリアのデザイン */
    .sun-card {
        background-color: #f0f8ff;
        padding: 15px;
        border-radius: 12px;
        border: 1px solid #b0e0e6;
        margin-bottom: 15px;
        text-align: center;
        color: #333;
    }
    .golden-hour {
        background: linear-gradient(90deg, #ffecd2 0%, #fcb69f 100%);
        padding: 15px;
        border-radius: 12px;
        color: #a04000;
        font-weight: bold;
        text-align: center;
        margin-top: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 🔐 ログイン
# ==========================================
def check_password():
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
    if st.session_state['logged_in']:
        return True
    st.markdown("### 🔐 Login")
    with st.form("login_form"):
        password = st.text_input("Password", type="password")
        if st.form_submit_button("ログイン", type="primary"):
            correct = os.getenv("APP_PASSWORD") or st.secrets.get("APP_PASSWORD") or "admin123"
            if password == correct:
                st.session_state['logged_in'] = True
                st.rerun()
            else:
                st.error("パスワードが違います")
    return False

if not check_password():
    st.stop()

# ==========================================
# API & ツール関数
# ==========================================
if "GEMINI_API_KEY" in st.secrets:
    API_KEY = st.secrets["GEMINI_API_KEY"]
else:
    API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    st.error("APIキー設定エラー")
    st.stop()

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# 座標データ
CITIES = {
    "東京": {"lat": 35.6895, "lon": 139.6917},
    "大阪": {"lat": 34.6937, "lon": 135.5023},
    "京都": {"lat": 35.0116, "lon": 135.7681},
    "札幌": {"lat": 43.0618, "lon": 141.3545},
    "福岡": {"lat": 33.5904, "lon": 130.4017},
    "那覇": {"lat": 26.2124, "lon": 127.6809},
    "仙台": {"lat": 38.2682, "lon": 140.8694},
    "名古屋": {"lat": 35.1815, "lon": 136.9066},
}

def get_sun_data(lat, lon, date_str):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=sunrise,sunset&timezone=Asia%2FTokyo&start_date={date_str}&end_date={date_str}"
        r = requests.get(url)
        data = r.json()
        sunrise = data['daily']['sunrise'][0].split("T")[1]
        sunset = data['daily']['sunset'][0].split("T")[1]
        return sunrise, sunset
    except:
        return None, None

# バケツ管理
if 'selected_tags' not in st.session_state:
    st.session_state['selected_tags'] = []

def add_tag(tag_text):
    if tag_text not in st.session_state['selected_tags']:
        st.session_state['selected_tags'].append(tag_text)

def clear_tags():
    st.session_state['selected_tags'] = []

def create_grid(items, cols=4):
    """
    PC: 4列
    スマホ: CSSで幅50%に強制され、gapが0になるため「2列 x 2行」に折り返される
    """
    for i in range(0, len(items), cols):
        columns = st.columns(cols)
        for j, col in enumerate(columns):
            if i + j < len(items):
                label, val = items[i + j]
                if col.button(label, key=f"btn_{val}_{i}_{j}", use_container_width=True):
                    add_tag(val)

# ==========================================
# 画面構成
# ==========================================
st.markdown("<h3 style='text-align: center; margin:0;'>🇯🇵 Video Planner & Sun</h3>", unsafe_allow_html=True)

# --- 🛒 バケツエリア ---
if st.session_state['selected_tags']:
    tags_html = "".join([f'<span class="selected-tag">{tag}</span>' for tag in st.session_state['selected_tags']])
    st.markdown(f'<div class="tag-container">{tags_html}</div>', unsafe_allow_html=True)
    if st.button("🗑️ 選択リセット", use_container_width=True):
        clear_tags()
        st.rerun()
else:
    st.markdown("<div class='tag-container' style='color:#999; font-size:12px; padding-top:10px;'>スタンプを押すとここに追加されます</div>", unsafe_allow_html=True)

# --- メインタブ ---
main_tab1, main_tab2 = st.tabs(["🧩 プラン作成", "☀️ 太陽シミュ"])

# ----------------------------------
# タブ1: プラン作成（スタンプ）
# ----------------------------------
with main_tab1:
    sub_t1, sub_t2, sub_t3 = st.tabs(["✨ 雰囲気", "📍 ロケ地", "🕒 時間"])
    
    with sub_t1:
        items_atm = [
            ("🎞️ レトロ", "昭和レトロ"), ("🏠 ノスタル", "ノスタルジック"), ("☕ チル", "チル"),
            ("🤫 静寂", "静か"), ("😌 リラックス", "落ち着く"), ("🍃 廃墟感", "廃墟"),
            ("🥀 退廃美", "退廃的"), ("🤖 サイバー", "サイバーパンク"), ("🚀 近未来", "SF"),
            ("🏙️ 都会的", "都会的"), ("💎 高級感", "ラグジュアリー"), ("⚡ 活気", "エネルギッシュ"),
            ("👥 雑踏", "人混み"), ("🌸 儚い", "儚い"), ("🎨 映え", "カラフル"),
            ("🎥 シネマ", "映画風"), ("🖤 無機質", "無機質"), ("👻 不気味", "不気味")
        ]
        create_grid(items_atm, cols=4)

    with sub_t2:
        items_loc = [
            ("⛩️ 神社", "神社"), ("🏯 寺院", "寺院"), ("🇯🇵 和風", "和風建築"),
            ("🌉 橋", "橋"), ("🌊 海", "海"), ("🛶 川", "川"),
            ("🚢 港", "港"), ("🌳 公園", "公園"), ("🌲 森林", "森林"),
            ("🌿 緑", "自然"), ("🏙️ ビル", "高層ビル"), ("🏢 屋上", "屋上"),
            ("🔭 展望", "展望台"), ("🛤️ 路地裏", "路地裏"), ("🏮 横丁", "飲み屋街"),
            ("🏭 工場", "工場"), ("📦 倉庫", "倉庫"), ("⚙️ 鉄骨", "鉄骨"),
            ("🛍️ 商店街", "商店街"), ("🏛️ 建築", "有名建築"), ("🚉 駅", "駅構内"),
            ("🚇 地下", "地下通路"), ("♨️ 温泉", "温泉街"), ("🌾 田舎", "田園")
        ]
        create_grid(items_loc, cols=4)

    with sub_t3:
        items_time = [
            ("🌅 早朝", "早朝"), ("🚷 無人", "無人"), ("🌞 昼間", "昼間"),
            ("🔵 青空", "青空"), ("🌇 夕方", "夕暮れ"), ("🧡 マジック", "マジックアワー"),
            ("🌃 深夜", "深夜"), ("🌑 暗闇", "暗闇"), ("✨ 夜景", "夜景"),
            ("💡 ネオン", "ネオン"), ("☔ 雨", "雨"), ("💧 反射", "リフレクション"),
            ("☁️ 曇り", "曇り"), ("🌸 春/桜", "桜"), ("🍂 秋/紅葉", "紅葉"),
            ("❄️ 冬/雪", "雪")
        ]
        create_grid(items_time, cols=4)

    # 検索フォーム
    st.markdown("---")
    st.markdown("##### 📍 条件指定")
    with st.form(key='search_form'):
        c1, c2 = st.columns(2)
        with c1:
            target_area = st.text_input("エリア", placeholder="例: 大阪")
        with c2:
            style = st.radio("スタイル", ["👤 一人", "👥 複数"])
        
        default_text = " ".join(st.session_state['selected_tags'])
        additional_text = st.text_input("キーワード", placeholder="例: 穴場", value="")
        
        st.markdown("<br>", unsafe_allow_html=True)
        submit_button = st.form_submit_button(label='🇯🇵 検索スタート', type="primary", use_container_width=True)

    if submit_button:
        area_query = target_area if target_area else "日本国内"
        final_query = f"{default_text} {additional_text}".strip()
        
        if not final_query and not target_area:
            st.warning("タグかエリアを入力してください")
        else:
            with st.spinner('AIプランニング中...'):
                try:
                    prompt = f"""
                    エリア: {area_query}
                    条件: {final_query}
                    スタイル: {style}
                    
                    動画撮影スポットを5つ提案。
                    出力JSON:
                    name, search_name(GoogleMap用), area, reason, permission, 
                    video_idea, script, fashion, bgm, sns_info, lat, lon
                    """
                    response = model.generate_content(prompt)
                    text_resp = response.text.strip()
                    if text_resp.startswith("```json"): text_resp = text_resp[7:-3]
                    elif text_resp.startswith("```"): text_resp = text_resp[3:-3]
                    spots = json.loads(text_resp)
                    
                    st.success("✅ プラン作成完了")
                    save_text = f"【撮影プラン】\nエリア: {area_query}\nテーマ: {final_query}\n\n"
                    
                    df = pd.DataFrame(spots)
                    st.map(df, latitude='lat', longitude='lon', size=20, color='#FF4B4B')

                    for i, spot in enumerate(spots, 1):
                        save_text += f"[{i}] {spot['name']}\n ポイント: {spot['reason']}\n 脚本: {spot['script']}\n MAP: {spot['search_name']}\n\n"
                        with st.expander(f"📍 {spot['name']}", expanded=False):
                            perm = spot['permission']
                            if "禁止" in perm or "許可" in perm: st.error(f"⚠️ {perm}")
                            else: st.caption(f"ℹ️ {perm}")
                            t1, t2 = st.tabs(["🎥 構成・脚本", "👗 服装・地図"])
                            with t1:
                                st.info(f"**{spot['video_idea']}**")
                                st.code(spot['script'], language="text")
                            with t2:
                                st.write(f"👗 {spot['fashion']}")
                                q = spot['search_name'].replace(" ", "+")
                                st.link_button("📍 Googleマップ", f"https://www.google.com/maps/search/?api=1&query={q}", use_container_width=True)

                    st.download_button("📥 テキスト保存", save_text, "plan.txt", use_container_width=True)

                except Exception as e:
                    st.error("エラーが発生しました")
                    st.write(e)

# ----------------------------------
# タブ2: 太陽シミュレーション
# ----------------------------------
with main_tab2:
    st.markdown("##### ☀️ Sun Tracker")
    st.caption("撮影日の太陽の動きをシミュレーションします")
    
    col_city, col_date = st.columns(2)
    with col_city:
        city_name = st.selectbox("都市を選択", list(CITIES.keys()))
    with col_date:
        target_date = st.date_input("撮影日", datetime.date.today())
    
    if st.button("計算する 🌤️", use_container_width=True):
        lat = CITIES[city_name]["lat"]
        lon = CITIES[city_name]["lon"]
        date_str = target_date.strftime("%Y-%m-%d")
        
        sunrise, sunset = get_sun_data(lat, lon, date_str)
        
        if sunrise and sunset:
            sr_h, sr_m = map(int, sunrise.split(":"))
            ss_h, ss_m = map(int, sunset.split(":"))
            
            golden_start = f"{ss_h}:{(ss_m - 30):02d}" if ss_m >= 30 else f"{ss_h-1}:{(ss_m + 30):02d}"
            golden_end = f"{ss_h}:{(ss_m + 15):02d}" if ss_m + 15 < 60 else f"{ss_h+1}:{(ss_m + 15 - 60):02d}"
            
            st.markdown(f"""
            <div class="sun-card">
                <h4>📅 {date_str} ({city_name})</h4>
                <p><strong>🌅 日の出:</strong> {sunrise}</p>
                <p><strong>🌞 南中 (目安):</strong> 12:00頃 (南)</p>
                <p><strong>🌇 日の入り:</strong> {sunset}</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class="golden-hour">
                ✨ マジックアワー (Golden Hour)<br>
                {golden_start} 〜 {golden_end}<br>
                <span style="font-size:0.8em; color:#333;">※空が最も美しく焼ける時間帯です</span>
            </div>
            """, unsafe_allow_html=True)
            
            st.info("🧭 **太陽の方角ガイド**\n\n"
                    f"・ **{sunrise}頃**: 東から昇ります\n"
                    "・ **10:00頃**: 南東 (順光で撮るなら北西向き)\n"
                    "・ **14:00頃**: 南西 (サイド光が良い感じ)\n"
                    f"・ **{sunset}頃**: 西に沈みます (逆光シルエットのチャンス)")
        else:
            st.error("データの取得に失敗しました。")