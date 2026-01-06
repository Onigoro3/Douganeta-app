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
st.set_page_config(page_title="Japan Video Planner", layout="wide", initial_sidebar_state="collapsed")

# ==========================================
# 🎨 CSSデザイン
# ==========================================
st.markdown("""
    <style>
    /* ヘッダー削除・余白調整 */
    header[data-testid="stHeader"], footer {display: none !important;}
    .block-container {
        padding-top: 140px !important;
        padding-bottom: 5rem !important;
        padding-left: 0.2rem !important;
        padding-right: 0.2rem !important;
    }

    /* 固定ヘッダー */
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
    .tag-container {
        text-align: center;
        min-height: 30px;
        margin-bottom: 5px;
    }
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

    /* 外部リンクボタン */
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
        transition: all 0.2s;
        font-size: 13px;
        height: 40px;
    }
    .custom-link-btn:hover {
        border-color: #FF4B4B;
        color: #FF4B4B;
        background-color: #f0f2f6;
    }

    /* タブデザイン */
    div[data-baseweb="tab-list"] {
        background-color: transparent !important;
        margin-bottom: 10px;
    }
    button[data-baseweb="tab"] {
        color: #cccccc !important;
        font-weight: bold !important;
        background-color: transparent !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #FF4B4B !important;
        border-bottom-color: #FF4B4B !important;
    }
    div[data-baseweb="tab-highlight"] {
        background-color: #FF4B4B !important;
    }

    /* スマホ2列強制 */
    @media (max-width: 768px) {
        [data-testid="stHorizontalBlock"] {
            flex-wrap: wrap !important;
            gap: 0 !important;
            padding: 0 !important;
        }
        div[data-testid="column"] {
            flex: 0 0 50% !important;
            width: 50% !important;
            max-width: 50% !important;
            min-width: 50% !important;
            padding: 2px !important;
            margin: 0 !important;
        }
        .stButton > button {
            font-size: 11px !important;
            padding: 2px 4px !important;
            min-height: 42px !important;
        }
    }

    /* 一般ボタン */
    .stButton > button {
        width: 100% !important;
        border-radius: 8px !important;
        min-height: 3.5rem;
        font-weight: bold !important;
        background-color: #ffffff !important;
        color: #262730 !important;
        border: 1px solid #d0d7de !important;
    }
    .stButton > button:active {
        background-color: #FF4B4B !important;
        color: #ffffff !important;
        border-color: #FF4B4B !important;
    }
    
    /* カード類 */
    .sun-card, .info-card {
        background-color: #262730;
        padding: 15px;
        border-radius: 12px;
        border: 1px solid #444;
        margin-bottom: 15px;
        color: #fff;
    }
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
model = genai.GenerativeModel('gemini-2.0-flash-exp') 

CITIES = {
    "東京": {"lat": 35.6895, "lon": 139.6917},
    "大阪": {"lat": 34.6937, "lon": 135.5023},
    "京都": {"lat": 35.0116, "lon": 135.7681},
    "札幌": {"lat": 43.0618, "lon": 141.3545},
    "福岡": {"lat": 33.5904, "lon": 130.4017},
    "那覇": {"lat": 26.2124, "lon": 127.6809},
}

def get_sun_data(lat, lon, date_str):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=sunrise,sunset&timezone=Asia%2FTokyo&start_date={date_str}&end_date={date_str}"
        r = requests.get(url)
        data = r.json()
        return data['daily']['sunrise'][0].split("T")[1], data['daily']['sunset'][0].split("T")[1]
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
    """共通のスポットカード表示関数"""
    card_title = f"📍 {spot.get('name', '名称不明')} ({spot.get('area', '')})"
    
    # 確信度表示（画像検索用）
    if 'confidence' in spot:
        conf = spot['confidence']
        icon = "🟢" if conf == "高" else "🟡" if conf == "中" else "🔴"
        card_title += f" {icon}"

    with st.expander(card_title, expanded=True if index==0 else False):
        if 'lat' in spot and 'lon' in spot and spot['lat'] != 0:
            try:
                df_map = pd.DataFrame({'lat': [spot['lat']], 'lon': [spot['lon']]})
                st.map(df_map, size=20, color='#FF4B4B', use_container_width=True)
            except: pass
            
        st.caption("👇 アクション (アプリで開く)")
        b1, b2, b3 = st.columns(3)
        q_enc = urllib.parse.quote(spot.get('search_name', spot.get('name', '')))
        
        url_map = f"https://www.google.com/maps/search/?api=1&query={q_enc}"
        url_img = f"https://www.google.com/search?q={q_enc}+実写+風景&tbm=isch"
        url_web = f"https://www.google.com/search?q={q_enc}"
        
        with b1: st.markdown(f'<a href="{url_map}" target="_blank" class="custom-link-btn">📍 マップ</a>', unsafe_allow_html=True)
        with b2: st.markdown(f'<a href="{url_img}" target="_blank" class="custom-link-btn">📷 写真検索</a>', unsafe_allow_html=True)
        with b3: st.markdown(f'<a href="{url_web}" target="_blank" class="custom-link-btn">🌐 検索</a>', unsafe_allow_html=True)

        st.markdown("---")
        st.write(f"**分析・理由:** {spot.get('reason', '')}")
        perm = spot.get('permission', '要確認')
        st.caption(f"ℹ️ {perm}")

# ==========================================
# 画面構成
# ==========================================

# 固定ヘッダー
header_html = f"""
<div class="sticky-header">
    <div style="text-align:center; color:white; font-size:14px; margin-bottom:5px;">🇯🇵 Japan Video Planner</div>
    <div class="tag-container">
"""
if st.session_state['selected_tags']:
    for tag in st.session_state['selected_tags']: header_html += f'<span class="selected-tag">{tag}</span>'
else: header_html += '<span style="color:#aaa; font-size:11px;">👇 スタンプを押すとここに追加されます</span>'
header_html += "</div></div>"
st.markdown(header_html, unsafe_allow_html=True)

# メインタブ
tab1, tab2, tab3, tab4 = st.tabs(["🧩 プラン作成", "🔍 ワード検索", "🕵️‍♂️ 画像特定", "☀️ 太陽シミュ"])

# ----------------------------------
# 1. プラン作成 (スタンプ)
# ----------------------------------
with tab1:
    if st.button("🗑️ タグクリア", use_container_width=True):
        clear_tags()
        st.rerun()

    sub_t1, sub_t2, sub_t3 = st.tabs(["✨ 雰囲気", "📍 ロケ地", "🕒 時間"])
    with sub_t1:
        items = [("🎞️ レトロ", "昭和レトロ"), ("🏠 ノスタル", "ノスタルジック"), ("☕ チル", "チル"), ("🤫 静寂", "静か"), ("🍃 廃墟感", "廃墟"), ("🤖 サイバー", "サイバーパンク"), ("🚀 近未来", "SF"), ("🏙️ 都会的", "都会的"), ("💎 高級感", "ラグジュアリー"), ("🎨 映え", "カラフル"), ("🎥 シネマ", "映画風"), ("👻 不気味", "不気味")]
        create_grid(items)
    with sub_t2:
        items = [("⛩️ 神社", "神社"), ("🏯 寺院", "寺院"), ("🇯🇵 和風", "和風建築"), ("🌉 橋", "橋"), ("🌊 海", "海"), ("🌳 公園", "公園"), ("🌿 緑", "自然"), ("🏙️ ビル", "高層ビル"), ("🛤️ 路地裏", "路地裏"), ("🏮 横丁", "飲み屋街"), ("🏭 工場", "工場"), ("⚙️ 鉄骨", "鉄骨"), ("🚉 駅", "駅構内"), ("♨️ 温泉", "温泉街")]
        create_grid(items)
    with sub_t3:
        items = [("🌅 早朝", "早朝"), ("🚷 無人", "無人"), ("🌞 昼間", "昼間"), ("🌇 夕方", "夕暮れ"), ("🧡 マジック", "マジックアワー"), ("🌃 深夜", "深夜"), ("✨ 夜景", "夜景"), ("💡 ネオン", "ネオン"), ("☔ 雨", "雨"), ("🌸 春", "桜"), ("🍂 秋", "紅葉"), ("❄️ 冬", "雪")]
        create_grid(items)

    st.markdown("---")
    with st.form("stamp_search"):
        area = st.text_input("エリア (任意)", placeholder="例: 大阪")
        kw = st.text_input("キーワード (任意)", placeholder="例: 穴場")
        if st.form_submit_button("🇯🇵 検索スタート", type="primary", use_container_width=True):
            with st.spinner('AIがプラン作成中...'):
                prompt = f"""
                ターゲットエリア: {area or '日本全国'}
                条件: {' '.join(st.session_state['selected_tags'])} {kw}
                
                【重要】
                ターゲットエリアに具体的な地名（例: 新宿、梅田、沖縄など）が指定されている場合、
                必ず**そのエリア内**にあるスポットのみを提案してください。
                エリア外のスポットは除外してください。
                
                日本の撮影スポットを5つ提案。
                出力JSONのみ: [{{ "name": "...", "search_name": "...", "area": "...", "reason": "...", "permission": "...", "lat": 0.0, "lon": 0.0 }}]
                """
                try:
                    res = model.generate_content(prompt)
                    json_str = re.search(r'\[.*\]', res.text, re.DOTALL).group(0)
                    spots = json.loads(json_str)
                    st.success("✅ 作成完了")
                    for i, s in enumerate(spots): render_spot_card(s, i)
                except: st.error("検索に失敗しました")

# ----------------------------------
# 2. ワード検索
# ----------------------------------
with tab2:
    st.markdown("##### 🔍 言葉から探す")
    st.caption("地名を含めると、その場所の中から詳しく探します")
    word_query = st.text_input("検索ワード", placeholder="例: サイバーパンク 新宿、レトロな路地裏 大阪...")
    
    if st.button("🚀 AI検索", type="primary", use_container_width=True):
        if not word_query:
            st.warning("ワードを入力してください")
        else:
            with st.spinner('AIが翻訳＆リサーチ中...'):
                try:
                    # 地名縛りを強化したプロンプト
                    prompt = f"""
                    ユーザーの検索ワード: 「{word_query}」
                    
                    【最重要ルール: 地名の厳守】
                    検索ワードの中に「地名（都道府県、市区町村、駅名、地域名）」が含まれているか分析してください。
                    
                    1. **地名が含まれている場合**:
                       - 必ず**その指定された地域内（そのエリアの中）**にあるスポットだけを5つ探してください。
                       - 例: 「新宿」なら新宿区内（歌舞伎町、西新宿など）限定。「東京」なら都内限定。
                       - 指定エリア外の場所は提案しないでください。

                    2. **地名が含まれていない場合**:
                       - 日本全国から、ワードのニュアンスに合う場所を探してください。

                    タスク:
                    - ワードの雰囲気（例: サイバーパンク -> Neon/Futuristic）を解釈し、それに合う実写撮影スポットを特定。
                    
                    出力JSONのみ:
                    [
                        {{
                            "name": "スポット名",
                            "search_name": "Google検索用",
                            "area": "都道府県・市区町村",
                            "reason": "選定理由",
                            "english_keyword": "翻訳された英語KW",
                            "lat": 35.0,
                            "lon": 135.0
                        }}
                    ]
                    """
                    res = model.generate_content(prompt)
                    match = re.search(r'\[.*\]', res.text, re.DOTALL)
                    if match:
                        spots = json.loads(match.group(0))
                        en_kw = spots[0].get('english_keyword', '')
                        st.info(f"🔤 英語変換: **{en_kw}** の要素も含んで検索しました")
                        for i, s in enumerate(spots): render_spot_card(s, i)
                    else: st.error("AIからの応答エラー")
                except Exception as e: st.error(f"エラー: {e}")

# ----------------------------------
# 3. 画像検索 (特定モード)
# ----------------------------------
with tab3:
    st.markdown("##### 🕵️‍♂️ 画像から場所特定")
    st.caption("画像をドロップしてください。AIが場所を特定、または似たロケ地を探します。")
    
    uploaded_file = st.file_uploader("画像をアップロード", type=["jpg", "png", "jpeg"])
    
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="解析対象の画像", use_container_width=True)
        
        if st.button("🗺️ 場所を特定する", type="primary", use_container_width=True):
            with st.spinner('AIが画像を凝視中...'):
                try:
                    prompt = """
                    あなたはロケ地特定のプロフェッショナルです。
                    この画像を分析し、撮影された場所、またはその雰囲気に酷似した日本国内の場所を特定してください。
                    
                    【ルール】
                    1. 特定のランドマークなら、その場所を1つピンポイントで提示。
                    2. 特定できない一般的な風景なら、似た雰囲気が撮れる日本の場所を3つ提案。
                    
                    出力JSONのみ:
                    [
                        {{
                            "name": "スポット名",
                            "search_name": "Google検索用(県名含む)",
                            "area": "都道府県",
                            "reason": "画像の特徴（例：看板、建物から特定）",
                            "confidence": "高/中/低",
                            "lat": 35.6895,
                            "lon": 139.6917
                        }}
                    ]
                    """
                    res = model.generate_content([prompt, image])
                    match = re.search(r'\[.*\]', res.text, re.DOTALL)
                    if match:
                        spots = json.loads(match.group(0))
                        st.success("✅ 分析完了")
                        
                        if spots:
                            top = spots[0]
                            if top.get('confidence') == '高':
                                st.info(f"🎯 **特定しました:** これは **{top['name']}** ({top['area']}) の可能性が高いです。")
                            else:
                                st.warning(f"🤔 完全に特定はできませんでしたが、**{top['area']}** 周辺、または以下の場所が似ています。")

                        for i, s in enumerate(spots): render_spot_card(s, i)
                    else: st.error("解析できませんでした")
                except Exception as e: st.error(f"エラー: {e}")

# ----------------------------------
# 4. 太陽シミュ
# ----------------------------------
with tab4:
    st.markdown("##### ☀️ Sun Tracker")
    c1, c2 = st.columns(2)
    with c1: city = st.selectbox("都市", list(CITIES.keys()))
    with c2: date = st.date_input("日付", datetime.date.today())
    
    if st.button("計算 🌤️", use_container_width=True):
        sr, ss = get_sun_data(CITIES[city]["lat"], CITIES[city]["lon"], date.strftime("%Y-%m-%d"))
        if sr:
            st.markdown(f"""
            <div class="sun-card">
                <h4>{city} ({date})</h4>
                <p>🌅 日出: {sr} | 🌇 日没: {ss}</p>
                <div style="background:#d4af37; color:#000; padding:5px; border-radius:5px; margin-top:10px;">
                ✨ マジックアワー: 日没前後30分
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.info(f"🧭 **太陽の方角**: {sr}頃は東、12時は南、{ss}頃は西です。")