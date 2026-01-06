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
# 🎨 CSSデザイン (凝縮 & 精度向上版)
# ==========================================
st.markdown("""
    <style>
    /* ヘッダー削除・余白極小化 */
    header[data-testid="stHeader"], footer {display: none !important;}
    
    .block-container {
        padding-top: 120px !important; /* 固定ヘッダー分 */
        padding-bottom: 3rem !important;
        padding-left: 0.2rem !important;
        padding-right: 0.2rem !important;
    }

    /* 固定ヘッダー (コンパクト化) */
    .sticky-header {
        position: fixed; top: 0; left: 0; right: 0; z-index: 9999;
        background-color: rgba(20, 20, 20, 0.98); /* より濃い黒で引き締め */
        backdrop-filter: blur(10px);
        padding: 5px; border-bottom: 1px solid #444;
        box-shadow: 0 4px 6px rgba(0,0,0,0.5);
    }
    
    /* タグコンテナ */
    .tag-container { text-align: center; min-height: 25px; margin-top: 2px; }
    .selected-tag {
        display: inline-block; background-color: #FF4B4B; color: white !important;
        padding: 2px 8px; margin: 1px; border-radius: 12px; font-size: 10px; font-weight: bold;
    }

    /* 検索結果カード (余白詰め) */
    div[data-testid="stExpander"] {
        margin-bottom: 5px !important; /* カード間の隙間を詰める */
        border: 1px solid #444 !important;
        border-radius: 8px !important;
        background-color: #262730 !important;
    }
    div[data-testid="stExpander"] details {
        padding: 0 !important;
    }
    
    /* リンクボタン (高さ調整) */
    .custom-link-btn {
        display: inline-flex; align-items: center; justify-content: center;
        width: 100%; padding: 0.2rem; margin-bottom: 0.2rem; font-weight: bold;
        color: #262730; background-color: #ffffff; border: 1px solid #d0d7de;
        border-radius: 6px; text-decoration: none !important; font-size: 12px; height: 35px;
    }
    
    /* スマホ2列強制 (隙間なし) */
    @media (max-width: 768px) {
        div[data-testid="column"] { 
            flex: 0 0 50% !important; width: 50% !important; 
            min-width: 50% !important; padding: 1px !important; 
        }
    }
    
    /* ボタンデザイン */
    .stButton > button { 
        width: 100% !important; border-radius: 6px !important; 
        min-height: 3rem !important; font-weight: bold !important; 
        font-size: 0.85rem !important; margin: 0 !important;
    }
    
    /* タブの余白削除 */
    .stTabs [data-baseweb="tab-list"] { gap: 2px; }
    .stTabs [data-baseweb="tab"] { padding: 5px 10px !important; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 🔐 認証 & API設定
# ==========================================
def check_password():
    if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
    if st.session_state['logged_in']: return True
    st.markdown("### 🔐 Login")
    with st.form("login"):
        pwd = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            correct = os.getenv("APP_PASSWORD") or st.secrets.get("APP_PASSWORD") or "admin123"
            if pwd == correct:
                st.session_state['logged_in'] = True
                st.rerun()
    return False

if not check_password(): st.stop()

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("API Key not found")
    st.stop()

# 画像認識に強いモデル
model = genai.GenerativeModel('models/gemini-2.5-flash')

# ==========================================
# 🛠️ 外部API連携 (精度強化版)
# ==========================================
def fetch_google_images(query_keywords):
    """
    Google Custom Search APIで画像を検索
    ★修正点: 雰囲気ワードをクエリに含め、スイーツなどを除外する
    """
    url = "https://www.googleapis.com/customsearch/v1"
    
    # 検索クエリの作成: 
    # 1. ユーザーのキーワードを入れる
    # 2. "scenery street" (風景) を追加
    # 3. "-food -sweets -anime" (ノイズ) を除外
    q = f"{query_keywords} scenery street photography -food -sweets -cake -menu -anime -illustration -poster"
    
    params = {
        "q": q,
        "cx": st.secrets["GOOGLE_CSE_ID"],
        "key": st.secrets["GOOGLE_CSE_KEY"],
        "searchType": "image",
        "num": 2,           # 取得枚数
        "imgType": "photo", # 実写のみ
        "gl": "jp",         # 日本の検索結果
        "safe": "off"
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
# 🍱 UIパーツ (凝縮レイアウト)
# ==========================================
def render_spot_result(spot, index, extra_keywords=""):
    """
    スポット表示
    extra_keywords: 「サイバーパンク」などの雰囲気ワードを受け取る
    """
    # タイトル部分
    title = f"📍 {spot.get('name', '')}"
    if 'confidence' in spot:
        icon = {"高":"🟢","中":"🟡","低":"🔴"}.get(spot['confidence'],"")
        title += f" {icon}"
    
    with st.expander(title, expanded=True if index==0 else False):
        # 1. 検索実行 (場所名 + エリア + 雰囲気ワード)
        # ここで「新宿 サイバーパンク」などのワードを合成してAPIに投げる
        search_q = f"{spot['name']} {spot.get('area','')} {extra_keywords}"
        images = fetch_google_images(search_q)
        
        # 2. 画像表示 (レイアウト詰め)
        if images:
            st.image(images[0]['img'], use_container_width=True)
            st.markdown(f'<div style="text-align:right; font-size:10px;"><a href="{images[0]["link"]}" target="_blank" style="color:#aaa;">出典: {images[0]["title"][:15]}...</a></div>', unsafe_allow_html=True)
        
        # 3. マップ
        if spot.get('lat'):
            st.map(pd.DataFrame({'lat': [spot['lat']], 'lon': [spot['lon']]}), size=15, color='#FF4B4B', use_container_width=True)
        
        # 4. ボタン (横並びで詰める)
        q_enc = urllib.parse.quote(f"{spot['name']} {extra_keywords}")
        c1, c2, c3 = st.columns(3)
        with c1: st.markdown(f'<a href="https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(spot["name"])}" target="_blank" class="custom-link-btn">📍MAP</a>', unsafe_allow_html=True)
        with c2: st.markdown(f'<a href="https://www.google.com/search?q={q_enc}+scenery&tbm=isch" target="_blank" class="custom-link-btn">📷写真</a>', unsafe_allow_html=True)
        with c3: st.markdown(f'<a href="https://www.google.com/search?q={q_enc}" target="_blank" class="custom-link-btn">🌐検索</a>', unsafe_allow_html=True)
        
        st.caption(f"💡 {spot.get('reason', '')}")

# ==========================================
# 🖥️ メイン画面
# ==========================================

# バケツ (固定ヘッダー)
if 'selected_tags' not in st.session_state: st.session_state['selected_tags'] = []
tags_html = "".join([f'<span class="selected-tag">{t}</span>' for t in st.session_state['selected_tags']]) or '<span style="color:#aaa; font-size:10px;">スタンプ未選択</span>'
st.markdown(f'<div class="sticky-header"><div style="text-align:center; color:white; font-size:12px; margin-bottom:2px;">🇯🇵 Video Planner</div><div class="tag-container">{tags_html}</div></div>', unsafe_allow_html=True)

# タブ
tab1, tab2, tab3, tab4 = st.tabs(["🧩プラン", "🔍ワード", "🕵️画像", "☀️太陽"])

# --- 1. プラン作成 ---
with tab1:
    if st.button("🗑️ クリア", key="clr1"): st.session_state['selected_tags'] = []; st.rerun()
    
    # スタンプグリッド (関数化してコンパクトに)
    def grid(items):
        for i in range(0, len(items), 4):
            cols = st.columns(4)
            for j, c in enumerate(cols):
                if i+j < len(items):
                    l, v = items[i+j]
                    if c.button(l, key=f"s_{v}"): 
                        if v not in st.session_state['selected_tags']: st.session_state['selected_tags'].append(v)
                        st.rerun()

    t1, t2, t3 = st.tabs(["雰囲気", "場所", "時間"])
    with t1: grid([("🎞️レトロ","昭和レトロ"),("🏠ノスタル","ノスタルジック"),("☕チル","チル"),("🤫静寂","静か"),("🍃廃墟","廃墟"),("🤖サイバー","サイバーパンク"),("🚀SF","SF近未来"),("🏙️都会","都会的"),("💎高級","ラグジュアリー"),("🎨映え","カラフル"),("🎥映画","映画風"),("👻不気味","不気味")])
    with t2: grid([("⛩️神社","神社"),("🏯寺院","寺院"),("🇯🇵和風","和風建築"),("🌉橋","橋"),("🌊海","海"),("🌳公園","公園"),("🏙️ビル","高層ビル"),("🛤️路地","路地裏"),("🏭工場","工場"),("⚙️鉄骨","鉄骨"),("🚉駅","駅構内")])
    with t3: grid([("🌅早朝","早朝"),("🚷無人","無人"),("🌞昼間","昼間"),("🌇夕方","夕暮れ"),("🧡マジック","マジックアワー"),("🌃深夜","深夜"),("✨夜景","夜景"),("☔雨","雨"),("❄️冬","雪")])
    
    with st.form("f1"):
        c_a, c_k = st.columns(2)
        area = c_a.text_input("エリア", placeholder="例: 新宿")
        kw = c_k.text_input("KW", placeholder="例: 穴場")
        if st.form_submit_button("🚀 検索", type="primary"):
            # 検索用の雰囲気タグをまとめる
            context_tags = " ".join(st.session_state['selected_tags'])
            
            prompt = f"""
            エリア: {area or '日本全国'}
            条件: {context_tags} {kw}
            日本の実写撮影スポットを5つ提案。
            出力JSON: [{{'name':'','search_name':'Google検索用(地名含む)','area':'','reason':'','lat':0.0,'lon':0.0}}]
            """
            try:
                res = model.generate_content(prompt)
                spots = json.loads(re.search(r'\[.*\]', res.text, re.DOTALL).group(0))
                
                # 画像検索のために、場所名だけでなく「タグ」「KW」も渡す
                extra_kw = f"{context_tags} {kw}"
                for i, s in enumerate(spots): render_spot_result(s, i, extra_keywords=extra_kw)
            except: st.error("検索失敗")

# --- 2. ワード検索 (精度強化) ---
with tab2:
    q_word = st.text_input("ワード", placeholder="例: サイバーパンク 新宿")
    if st.button("AI検索", key="btn_word", type="primary"):
        with st.spinner("解析中..."):
            prompt = f"""
            ワード「{q_word}」から、その「雰囲気(Vibe)」と「指定された地名」を分析せよ。
            地名がある場合はそのエリア内限定で探せ。
            出力JSON: [{{'name':'','search_name':'','area':'','reason':'','lat':0.0,'lon':0.0}}]
            """
            try:
                res = model.generate_content(prompt)
                spots = json.loads(re.search(r'\[.*\]', res.text, re.DOTALL).group(0))
                # 検索ワード自体を画像検索の補強に使う
                for i, s in enumerate(spots): render_spot_result(s, i, extra_keywords=q_word)
            except: st.error("エラー")

# --- 3. 画像特定 ---
with tab3:
    up = st.file_uploader("画像", type=["jpg","png","jpeg"])
    if up:
        img = Image.open(up)
        st.image(img, width=200)
        if st.button("特定", type="primary"):
            with st.spinner("OCR解析中..."):
                prompt = "画像内の文字・風景から日本国内の場所を特定。JSON:[{'name':'','search_name':'','area':'','reason':'','confidence':'高/中/低','lat':0.0,'lon':0.0}]"
                try:
                    res = model.generate_content([prompt, img])
                    spots = json.loads(re.search(r'\[.*\]', res.text, re.DOTALL).group(0))
                    for i, s in enumerate(spots): render_spot_result(s, i)
                except: st.error("解析失敗")

# --- 4. 太陽 ---
with tab4:
    c1, c2 = st.columns(2)
    city = c1.selectbox("都市", ["東京","大阪","京都","札幌","福岡","那覇"])
    date = c2.date_input("日付")
    coords = {"東京":(35.68,139.69),"大阪":(34.69,135.50),"京都":(35.01,135.76),"札幌":(43.06,141.35),"福岡":(33.59,130.40),"那覇":(26.21,127.68)}
    if st.button("計算"):
        sr, ss = get_sun_data(*coords[city], date.strftime("%Y-%m-%d"))
        if sr: st.info(f"🌅 {sr}  |  🌇 {ss}")