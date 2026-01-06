import streamlit as st
import google.generativeai as genai
import os
import json
import pandas as pd
import requests
import datetime
import re
import urllib.parse
import time
from PIL import Image
from dotenv import load_dotenv

# --- 設定の読み込み ---
load_dotenv()

# --- ページ設定 ---
st.set_page_config(page_title="Japan Video Planner", layout="wide", initial_sidebar_state="collapsed")

# ==========================================
# 🎨 CSSデザイン
# ==========================================
st.markdown("""
    <style>
    header[data-testid="stHeader"], footer {display: none !important;}
    .block-container {
        padding-top: 140px !important;
        padding-bottom: 5rem !important;
        padding-left: 0.2rem !important;
        padding-right: 0.2rem !important;
    }
    .sticky-header {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        z-index: 9999;
        background-color: rgba(30, 30, 30, 0.95);
        backdrop-filter: blur(10px);
        padding: 10px 5px 5px 5px;
        border-bottom: 1px solid #444;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .tag-container { text-align: center; min-height: 30px; }
    .selected-tag {
        display: inline-block;
        background-color: #FF4B4B;
        color: white !important;
        padding: 4px 10px;
        margin: 2px;
        border-radius: 15px;
        font-size: 11px;
        font-weight: bold;
    }
    .custom-link-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 100%;
        padding: 0.5rem;
        margin-bottom: 0.5rem;
        font-weight: bold;
        color: #262730;
        background-color: #ffffff;
        border: 1px solid #d0d7de;
        border-radius: 8px;
        text-decoration: none !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        font-size: 13px;
        height: 40px;
    }
    button[data-baseweb="tab"] { color: #cccccc !important; font-weight: bold !important; }
    button[data-baseweb="tab"][aria-selected="true"] { color: #FF4B4B !important; }
    @media (max-width: 768px) {
        div[data-testid="column"] {
            flex: 0 0 50% !important;
            width: 50% !important;
            min-width: 50% !important;
            padding: 2px !important;
        }
    }
    .stButton > button { width: 100% !important; border-radius: 8px !important; min-height: 3.5rem; font-weight: bold !important; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 🔐 ログイン
# ==========================================
def check_password():
    if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
    if st.session_state['logged_in']: return True
    st.markdown("### 🔐 Login")
    with st.form("login_form"):
        password = st.text_input("Password", type="password")
        if st.form_submit_button("ログイン", type="primary"):
            correct = os.getenv("APP_PASSWORD") or st.secrets.get("APP_PASSWORD") or "admin123"
            if password == correct:
                st.session_state['logged_in'] = True
                st.rerun()
            else: st.error("パスワードが違います")
    return False

if not check_password(): st.stop()

# ==========================================
# API設定
# ==========================================
if "GEMINI_API_KEY" in st.secrets:
    API_KEY = st.secrets["GEMINI_API_KEY"]
else:
    API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    st.error("APIキー設定エラー")
    st.stop()

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('models/gemini-2.5-flash') 

CITIES = {
    "東京": {"lat": 35.6895, "lon": 139.6917}, "大阪": {"lat": 34.6937, "lon": 135.5023},
    "京都": {"lat": 35.0116, "lon": 135.7681}, "札幌": {"lat": 43.0618, "lon": 141.3545},
    "福岡": {"lat": 33.5904, "lon": 130.4017}, "那覇": {"lat": 26.2124, "lon": 127.6809}
}

def get_sun_data(lat, lon, date_str):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=sunrise,sunset&timezone=Asia%2FTokyo&start_date={date_str}&end_date={date_str}"
        r = requests.get(url)
        return r.json()['daily']['sunrise'][0].split("T")[1], r.json()['daily']['sunset'][0].split("T")[1]
    except: return None, None

# バケツ管理
if 'selected_tags' not in st.session_state: st.session_state['selected_tags'] = []
def add_tag(tag_text):
    if tag_text not in st.session_state['selected_tags']: st.session_state['selected_tags'].append(tag_text)
def clear_tags(): st.session_state['selected_tags'] = []

def create_grid(items, cols=4):
    for i in range(0, len(items), cols):
        columns = st.columns(cols)
        for j, col in enumerate(columns):
            if i + j < len(items):
                label, val = items[i + j]
                if col.button(label, key=f"btn_{val}_{i}_{j}", use_container_width=True): add_tag(val)

def render_spot_card(spot, index):
    card_title = f"📍 {spot.get('name', '名称不明')} ({spot.get('area', '')})"
    if 'confidence' in spot:
        icon = {"高": "🟢", "中": "🟡", "低": "🔴"}.get(spot['confidence'], "⚪")
        card_title += f" {icon}"

    with st.expander(card_title, expanded=True if index==0 else False):
        if 'lat' in spot and 'lon' in spot and spot['lat'] != 0:
            df_map = pd.DataFrame({'lat': [spot['lat']], 'lon': [spot['lon']]})
            st.map(df_map, size=20, color='#FF4B4B', use_container_width=True)
            
        b1, b2, b3 = st.columns(3)
        q_enc = urllib.parse.quote(spot.get('search_name', spot.get('name', '')))
        url_map = f"https://www.google.com/maps/search/?api=1&query={q_enc}"
        url_img = f"https://www.google.com/search?q={q_enc}+実写+風景&tbm=isch"
        url_web = f"https://www.google.com/search?q={q_enc}"
        
        with b1: st.markdown(f'<a href="{url_map}" target="_blank" class="custom-link-btn">📍 マップ</a>', unsafe_allow_html=True)
        with b2: st.markdown(f'<a href="{url_img}" target="_blank" class="custom-link-btn">📷 写真</a>', unsafe_allow_html=True)
        with b3: st.markdown(f'<a href="{url_web}" target="_blank" class="custom-link-btn">🌐 検索</a>', unsafe_allow_html=True)

        st.write(f"**分析:** {spot.get('reason', '')}")
        st.caption(f"ℹ️ {spot.get('permission', '要確認')}")

# ==========================================
# 画面構成
# ==========================================

header_html = f"""
<div class="sticky-header">
    <div style="text-align:center; color:white; font-size:14px; margin-bottom:5px;">🇯🇵 Video Planner</div>
    <div class="tag-container">
"""
if st.session_state['selected_tags']:
    for tag in st.session_state['selected_tags']: header_html += f'<span class="selected-tag">{tag}</span>'
else: header_html += '<span style="color:#aaa; font-size:11px;">👇 スタンプを押すとここに追加されます</span>'
header_html += "</div></div>"
st.markdown(header_html, unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["🧩 プラン作成", "🔍 ワード検索", "🕵️‍♂️ 画像特定", "☀️ 太陽シミュ"])

# 1. プラン作成
with tab1:
    if st.button("🗑️ タグクリア", use_container_width=True):
        clear_tags(); st.rerun()
    sub1, sub2, sub3 = st.tabs(["✨ 雰囲気", "📍 ロケ地", "🕒 時間"])
    with sub1: create_grid([("🎞️ レトロ", "昭和レトロ"), ("🏠 ノスタル", "ノスタルジック"), ("☕ チル", "チル"), ("🤫 静寂", "静か"), ("🍃 廃墟感", "廃墟"), ("🤖 サイバー", "サイバーパンク"), ("🚀 近未来", "SF"), ("🏙️ 都会的", "都会的"), ("💎 高級感", "ラグジュアリー"), ("🎨 映え", "カラフル"), ("🎥 シネマ", "映画風")])
    with sub2: create_grid([("⛩️ 神社", "神社"), ("🏯 寺院", "寺院"), ("🇯🇵 和風", "和風建築"), ("🌉 橋", "橋"), ("🌊 海", "海"), ("🌳 公園", "公園"), ("🏙️ ビル", "高層ビル"), ("🛤️ 路地裏", "路地裏"), ("🏮 横丁", "飲み屋街"), ("🏭 工場", "工場"), ("⚙️ 鉄骨", "鉄骨"), ("🚉 駅", "駅構内")])
    with sub3: create_grid([("🌅 早朝", "早朝"), ("🚷 無人", "無人"), ("🌞 昼間", "昼間"), ("🌇 夕方", "夕暮れ"), ("🧡 マジックアワー", "マジックアワー"), ("🌃 深夜", "深夜"), ("✨ 夜景", "夜景"), ("💡 ネオン", "ネオン"), ("☔ 雨", "雨"), ("🌸 春", "桜"), ("🍂 秋", "紅葉"), ("❄️ 冬", "雪")])
    
    st.markdown("---")
    with st.form("stamp_search"):
        area = st.text_input("エリア", placeholder="例: 新宿")
        kw = st.text_input("キーワード", placeholder="例: 穴場")
        if st.form_submit_button("🇯🇵 検索スタート", type="primary", use_container_width=True):
            prompt = f"エリア: {area or '日本全国'} 条件: {' '.join(st.session_state['selected_tags'])} {kw}。日本の撮影スポット5つ。JSON形式 [{{'name': '...', 'search_name': '...', 'area': '...', 'reason': '...', 'permission': '...', 'lat': 0.0, 'lon': 0.0}}]"
            try:
                res = model.generate_content(prompt)
                spots = json.loads(re.search(r'\[.*\]', res.text, re.DOTALL).group(0))
                for i, s in enumerate(spots): render_spot_card(s, i)
            except: st.error("エラーが発生しました")

# 2. ワード検索
with tab2:
    st.markdown("##### 🔍 ワード検索")
    word_query = st.text_input("検索ワード", placeholder="例: サイバーパンク 新宿")
    if st.button("🚀 AI検索", type="primary", use_container_width=True):
        prompt = f"ワード: {word_query}。地名が含まれる場合はそのエリアを厳守。日本の実写スポット5つ。JSON [{{'name': '...', 'search_name': '...', 'area': '...', 'reason': '...', 'lat': 0.0, 'lon': 0.0}}]"
        try:
            res = model.generate_content(prompt)
            spots = json.loads(re.search(r'\[.*\]', res.text, re.DOTALL).group(0))
            for i, s in enumerate(spots): render_spot_card(s, i)
        except: st.error("エラーが発生しました")

# 3. 画像特定 (191行目付近: 風景・人物・絵画への対応強化)
with tab3:
    st.markdown("##### 🕵️‍♂️ 画像から場所特定")
    st.caption("風景写真、人物入りの写真、風景画、アニメの聖地巡礼用など、あらゆる画像に対応します。")
    uploaded_file = st.file_uploader("画像をアップロード", type=["jpg", "png", "jpeg"])
    if uploaded_file:
        img = Image.open(uploaded_file)
        st.image(img, caption="解析対象画像", use_container_width=True)
        if st.button("🗺️ AIによる場所特定 / 類似スポット検索", type="primary", use_container_width=True):
            with st.spinner('画像から背景情報をディープスキャン中...'):
                prompt = """
                あなたは「世界一のロケ地特定探偵」です。Gemini 2.5 Flashの能力をフル活用し、以下の画像を解析してください。
                
                【解析ミッション】
                1. 文字情報のスキャン(OCR): 看板、地名、道路標識、自販機、店名、電柱の住所表示を全て読み取ります。
                2. 背景・人物情報の分析:
                   - 風景画の場合: 描かれている山、川、建物の配置からモデルとなった可能性の高い実在の場所を推測。
                   - 人物が写っている場合: 人物を無視し、背後の街灯のデザイン、歩道のタイルの色、植生、背後のビルの形状から場所を絞り込みます。
                3. 特定の場所が見つからない場合: その画像が持つ「雰囲気」と「地形的特徴」を維持した、日本国内の代替ロケ地を提案してください。

                出力JSON形式のみ:
                [{"name": "スポット名", "search_name": "Google検索用(地名を含む具体的な名称)", "area": "都道府県", "reason": "なぜそこだと判断したかの具体的根拠(OCR結果や景観の特徴)", "confidence": "高/中/低", "lat": 0.0, "lon": 0.0}]
                """
                try:
                    res = model.generate_content([prompt, img])
                    spots_json = re.search(r'\[.*\]', res.text, re.DOTALL).group(0)
                    spots = json.loads(spots_json)
                    st.success("✅ 解析が完了しました")
                    for i, s in enumerate(spots): render_spot_card(s, i)
                except Exception as e:
                    st.error(f"解析エラーが発生しました。時間を置いて試してください。")

# 4. 太陽シミュ
with tab4:
    st.markdown("##### ☀️ Sun Tracker")
    c1, c2 = st.columns(2)
    with c1: city = st.selectbox("都市", list(CITIES.keys()))
    with c2: date = st.date_input("日付", datetime.date.today())
    if st.button("計算 🌤️", use_container_width=True):
        sr, ss = get_sun_data(CITIES[city]["lat"], CITIES[city]["lon"], date.strftime("%Y-%m-%d"))
        if sr: st.markdown(f"<div style='background:#262730; padding:15px; border-radius:10px;'><h4>{city}</h4><p>🌅 日出: {sr} | 🌇 日没: {ss}</p></div>", unsafe_allow_html=True)