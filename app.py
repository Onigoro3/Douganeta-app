import streamlit as st
import google.generativeai as genai
import os
import json
import pandas as pd
import requests
import datetime
import re
import urllib.parse
from PIL import Image
from dotenv import load_dotenv

# --- 設定の読み込み ---
load_dotenv()

# --- ページ設定 ---
st.set_page_config(page_title="Japan Video Planner Pro", layout="wide", initial_sidebar_state="collapsed")

# ==========================================
# 🎨 CSSデザイン (固定ヘッダー & レスポンシブ2列)
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
        position: fixed; top: 0; left: 0; right: 0; z-index: 9999;
        background-color: rgba(30, 30, 30, 0.95); backdrop-filter: blur(10px);
        padding: 10px 5px; border-bottom: 1px solid #444; box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .tag-container { text-align: center; min-height: 30px; }
    .selected-tag {
        display: inline-block; background-color: #FF4B4B; color: white !important;
        padding: 4px 10px; margin: 2px; border-radius: 15px; font-size: 11px; font-weight: bold;
    }
    /* 検索結果カード・リンクボタン */
    .result-card {
        background-color: #262730; border: 1px solid #444; padding: 10px;
        border-radius: 10px; margin-bottom: 20px; color: #fff;
    }
    .source-link {
        display: block; font-size: 12px; color: #FF4B4B !important;
        text-decoration: none; margin-top: 5px; font-weight: bold;
    }
    .custom-link-btn {
        display: inline-flex; align-items: center; justify-content: center;
        width: 100%; padding: 0.5rem; margin-bottom: 0.5rem; font-weight: bold;
        color: #262730; background-color: #ffffff; border: 1px solid #d0d7de;
        border-radius: 8px; text-decoration: none !important; font-size: 13px; height: 38px;
    }
    @media (max-width: 768px) {
        div[data-testid="column"] { flex: 0 0 50% !important; width: 50% !important; min-width: 50% !important; padding: 2px !important; }
    }
    .stButton > button { width: 100% !important; border-radius: 8px !important; min-height: 3.5rem; font-weight: bold !important; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 🔐 認証 & API設定
# ==========================================
def check_password():
    if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
    if st.session_state['logged_in']: return True
    with st.form("login"):
        pwd = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            if pwd == (st.secrets["APP_PASSWORD"] if "APP_PASSWORD" in st.secrets else "admin123"):
                st.session_state['logged_in'] = True
                st.rerun()
    return False

if not check_password(): st.stop()

# APIクライアント設定
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('models/gemini-2.5-flash')

# ==========================================
# 🛠️ 外部API連携関数
# ==========================================
def fetch_google_images(query):
    """Google Custom Search APIでネット全体から画像と元サイト情報を取得"""
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "q": query,
        "cx": st.secrets["GOOGLE_CSE_ID"],
        "key": st.secrets["GOOGLE_CSE_KEY"],
        "searchType": "image",
        "num": 3, "imgType": "photo", "gl": "jp"
    }
    try:
        res = requests.get(url, params=params).json()
        return [{"img": i["link"], "title": i["title"], "link": i["image"]["contextLink"]} for i in res.get("items", [])]
    except: return []

def get_sun_data(lat, lon, date_str):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=sunrise,sunset&timezone=Asia%2FTokyo&start_date={date_str}&end_date={date_str}"
        d = requests.get(url).json()['daily']
        return d['sunrise'][0].split("T")[1], d['sunset'][0].split("T")[1]
    except: return None, None

# ==========================================
# 🍱 UIパーツ
# ==========================================
def render_spot_result(spot, index):
    """画像・マップ・元サイト情報を統合して表示"""
    with st.container():
        st.markdown(f"### 📍 {spot['name']} ({spot['area']})")
        
        # 1. 画像検索の実行 (ネット全体から取得)
        search_kw = f"{spot['name']} {spot['area']} 風景 実写"
        images = fetch_google_images(search_kw)
        
        if images:
            # メイン画像表示
            st.image(images[0]['img'], use_container_width=True)
            # 元サイト情報
            st.markdown(f'<a href="{images[0]["link"]}" target="_blank" class="source-link">🔗 出典: {images[0]["title"]}</a>', unsafe_allow_html=True)
        
        # 2. マップ表示 (画像の下にポップ)
        if spot.get('lat'):
            df = pd.DataFrame({'lat': [spot['lat']], 'lon': [spot['lon']]})
            st.map(df, size=15, color='#FF4B4B', use_container_width=True)
        
        # 3. アクションボタン
        q_enc = urllib.parse.quote(spot['search_name'])
        col1, col2 = st.columns(2)
        with col1: st.markdown(f'<a href="https://www.google.com/maps/search/?api=1&query={q_enc}" target="_blank" class="custom-link-btn">📍 Googleマップ</a>', unsafe_allow_html=True)
        with col2: st.markdown(f'<a href="https://www.google.com/search?q={q_enc}+実写&tbm=isch" target="_blank" class="custom-link-btn">📷 写真をもっと見る</a>', unsafe_allow_html=True)
        
        st.info(f"💡 **理由:** {spot['reason']}")
        st.markdown("---")

# ==========================================
# 🖥️ メイン画面
# ==========================================

# 固定ヘッダー (バケツ)
if 'selected_tags' not in st.session_state: st.session_state['selected_tags'] = []
tags_html = "".join([f'<span class="selected-tag">{t}</span>' for t in st.session_state['selected_tags']]) or '<span style="color:#aaa; font-size:11px;">スタンプ選択中...</span>'
st.markdown(f'<div class="sticky-header"><div style="text-align:center; color:white; font-size:14px; margin-bottom:5px;">🇯🇵 Japan Video Planner</div><div class="tag-container">{tags_html}</div></div>', unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["🧩 プラン", "🔍 ワード検索", "🕵️ 画像特定", "☀️ 太陽"])

# --- 1. プラン作成 ---
with tab1:
    if st.button("🗑️ タグクリア"): st.session_state['selected_tags'] = []; st.rerun()
    def add(t): 
        if t not in st.session_state['selected_tags']: st.session_state['selected_tags'].append(t)
    
    # グリッド配置
    for label, tags in [("✨ 雰囲気", ["昭和レトロ","チル","サイバーパンク","都会的"]), ("📍 ロケ地", ["神社","海","工場","路地裏"]), ("🕒 時間", ["早朝","夕方","深夜","雨"])]:
        st.caption(label)
        cols = st.columns(4)
        for i, t in enumerate(tags):
            if cols[i].button(t, key=f"btn_{t}"): add(t); st.rerun()
    
    with st.form("f1"):
        area = st.text_input("地域名")
        if st.form_submit_button("🚀 検索", type="primary"):
            prompt = f"地域:{area or '日本'} 条件:{' '.join(st.session_state['selected_tags'])} 日本の実写ロケ地5つ提案。JSON: [{{'name':'','search_name':'','area':'','reason':'','lat':0.0,'lon':0.0}}]"
            res = model.generate_content(prompt)
            spots = json.loads(re.search(r'\[.*\]', res.text, re.DOTALL).group(0))
            for i, s in enumerate(spots): render_spot_result(s, i)

# --- 2. ワード検索 (日英同時検索) ---
with tab2:
    q_word = st.text_input("検索ワード (日本語でOK)", placeholder="例: 廃墟のような近未来...")
    if st.button("AIリサーチ開始", type="primary"):
        with st.spinner("AI翻訳 ＆ ネットリサーチ中..."):
            prompt = f"ワード「{q_word}」を英訳し、その両方のニュアンスに合致する日本国内の具体的な実写ロケ地を5つ特定。JSON:[{{'name':'','search_name':'','area':'','reason':'','lat':0.0,'lon':0.0}}]"
            res = model.generate_content(prompt)
            spots = json.loads(re.search(r'\[.*\]', res.text, re.DOTALL).group(0))
            for i, s in enumerate(spots): render_spot_result(s, i)

# --- 3. 画像特定 (OCR & 類似解析) ---
with tab3:
    up = st.file_uploader("画像をドロップ", type=["jpg","png","jpeg"])
    if up:
        img = Image.open(up)
        st.image(img, width=300)
        if st.button("🕵️ 場所を特定する", type="primary"):
            with st.spinner("背景文字(OCR)と景観をスキャン中..."):
                prompt = "画像内の文字(看板・標識)と風景を解析し、日本国内の場所を特定せよ。不明な場合は似た実写スポットを3つ。JSON:[{{'name':'','search_name':'','area':'','reason':'','lat':0.0,'lon':0.0}}]"
                res = model.generate_content([prompt, img])
                spots = json.loads(re.search(r'\[.*\]', res.text, re.DOTALL).group(0))
                for i, s in enumerate(spots): render_spot_result(s, i)

# --- 4. 太陽シミュ ---
with tab4:
    c1, c2 = st.columns(2)
    with c1: city = st.selectbox("都市", ["東京","大阪","京都","札幌","福岡"])
    with c2: date = st.date_input("日付")
    coords = {"東京":(35.68,139.69),"大阪":(34.69,135.50),"京都":(35.01,135.76),"札幌":(43.06,141.35),"福岡":(33.59,130.40)}
    if st.button("計算"):
        sr, ss = get_sun_data(*coords[city], date.strftime("%Y-%m-%d"))
        st.write(f"🌅 {sr} / 🌇 {ss}")