import streamlit as st
import google.generativeai as genai
import os
import json
import pandas as pd
from dotenv import load_dotenv

# --- 設定の読み込み ---
load_dotenv()

# --- ページ設定 ---
st.set_page_config(page_title="Tokyo Video Planner", layout="wide", initial_sidebar_state="collapsed")

# ==========================================
# 🎨 デザイン調整
# ==========================================
st.markdown("""
    <style>
    /* ヘッダー削除 */
    header[data-testid="stHeader"], footer {display: none !important;}
    
    /* スマホ向け全体余白調整 */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 5rem !important;
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
    }
    
    /* ボタンデザイン */
    .stButton > button {
        width: 100% !important;
        border-radius: 12px !important;
        min-height: 2.8rem !important;
        height: auto !important;
        padding: 4px !important;
        font-weight: bold !important;
        font-size: 0.8rem !important;
        line-height: 1.2 !important;
        white-space: normal !important;
        background-color: #f0f2f6; /* 薄いグレーで統一 */
        border: 1px solid #dcdcdc;
    }
    
    /* 選択されたタグのデザイン */
    .tag-container {
        background-color: #ffffff;
        padding: 10px;
        border-radius: 10px;
        margin-bottom: 10px;
        border: 2px solid #FF4B4B; /* 目立たせる */
        text-align: center;
        min-height: 50px;
    }
    .selected-tag {
        display: inline-block;
        background-color: #FF4B4B;
        color: white;
        padding: 6px 12px;
        margin: 3px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: bold;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    
    /* タブの調整 */
    button[data-baseweb="tab"] {
        font-size: 0.85rem !important;
        padding: 8px !important;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 🔐 簡易ログイン機能
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
# アプリ本体
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

# --- バケツ（選択タグ）管理 ---
if 'selected_tags' not in st.session_state:
    st.session_state['selected_tags'] = []

def add_tag(tag_text):
    if tag_text not in st.session_state['selected_tags']:
        st.session_state['selected_tags'].append(tag_text)

def clear_tags():
    st.session_state['selected_tags'] = []

# --- グリッド生成関数 ---
def create_grid(items, cols=4):
    """リストを受け取ってボタンを配置する"""
    for i in range(0, len(items), cols):
        columns = st.columns(cols)
        for j, col in enumerate(columns):
            if i + j < len(items):
                label, val = items[i + j]
                # ボタンのキーを一意にするためにindexを使用
                if col.button(label, key=f"btn_{val}_{i}_{j}", use_container_width=True):
                    add_tag(val)

# --- タイトル ---
st.markdown("<h4 style='text-align: center;'>🎬 Tokyo Video Planner</h4>", unsafe_allow_html=True)

# --- 🛒 バケツ表示 ---
if st.session_state['selected_tags']:
    tags_html = ""
    for tag in st.session_state['selected_tags']:
        tags_html += f'<span class="selected-tag">{tag}</span>'
    st.markdown(f'<div class="tag-container">{tags_html}</div>', unsafe_allow_html=True)
    
    if st.button("🗑️ リセット (最初から)", use_container_width=True):
        clear_tags()
        st.rerun()
else:
    st.markdown("<div class='tag-container' style='color:#bbb; padding-top:15px;'>スタンプを押すとここに追加されます</div>", unsafe_allow_html=True)

# --- スタンプ選択エリア ---
st.markdown("---")
tab1, tab2, tab3 = st.tabs(["✨ 雰囲気", "📍 場所", "🕒 時間/天気"])

with tab1:
    st.caption("欲しい「感情」や「スタイル」を選んでください")
    # キーワードをバラバラに分解
    items_atm = [
        ("🎞️ レトロ", "昭和レトロ"), ("🏠 ノスタルジー", "ノスタルジック"), 
        ("☕ チル", "チル"), ("🤫 静寂", "静か"),
        ("😌 リラックス", "落ち着く"), ("🍃 廃墟感", "廃墟"),
        ("🥀 退廃美", "退廃的"), ("🤖 サイバー", "サイバーパンク"),
        ("🚀 近未来", "近未来・SF"), ("🏙️ 都会的", "都会的"),
        ("💎 高級感", "ラグジュアリー"), ("⚡ 活気", "エネルギッシュ"),
        ("👥 雑踏", "人混み・雑踏"), ("🌸 儚い", "儚い・情緒的"),
        ("🎨 映え", "カラフル"), ("🎥 シネマ", "映画のような"),
        ("🖤 無機質", "無機質"), ("👻 不気味", "少し不気味")
    ]
    create_grid(items_atm, cols=4)

with tab2:
    st.caption("撮影したい「場所」の属性を選んでください")
    items_loc = [
        ("⛩️ 神社", "神社"), ("🏯 寺院", "寺院"),
        ("🇯🇵 和風", "和風建築"), ("🌉 橋", "橋"),
        ("🌊 海", "海"), ("🛶 川", "川"),
        ("🚢 港", "港・埠頭"), ("🌳 公園", "公園"),
        ("🌲 森林", "森林"), ("🌿 緑", "自然・緑"),
        ("🏙️ ビル群", "高層ビル"), ("🏢 屋上", "屋上"),
        ("🔭 展望台", "展望台"), ("🛤️ 路地裏", "路地裏"),
        ("🏮 横丁", "飲み屋街"), ("🏭 工場", "工場"),
        ("📦 倉庫", "倉庫"), ("⚙️ 鉄骨", "インダストリアル"),
        ("🛍️ 商店街", "商店街"), ("🏛️ 有名建築", "建築美"),
        ("🚉 駅", "駅構内"), ("🚇 地下", "地下通路")
    ]
    create_grid(items_loc, cols=4)

with tab3:
    st.caption("「時間帯」や「天候」の条件を選んでください")
    items_time = [
        ("🌅 早朝", "早朝"), ("🚷 無人", "人がいない"),
        ("🌞 昼間", "昼間"), ("🔵 青空", "青空"),
        ("🌇 夕方", "夕暮れ"), ("🧡 マジック", "マジックアワー"),
        ("🌃 深夜", "深夜"), ("🌑 暗闇", "暗闇"),
        ("✨ 夜景", "夜景"), ("💡 ネオン", "ネオン"),
        ("☔ 雨", "雨"), ("💧 反射", "リフレクション"),
        ("☁️ 曇り", "曇り"), ("🌸 春/桜", "桜"),
        ("🍂 秋/紅葉", "紅葉"), ("❄️ 冬", "冬")
    ]
    create_grid(items_time, cols=4)

# --- 検索実行フォーム ---
st.markdown("---")
with st.form(key='search_form'):
    style = st.radio("スタイル", ["👤 一人 (Vlog)", "👥 複数 (会話劇)"], horizontal=True)
    
    default_text = " ".join(st.session_state['selected_tags'])
    additional_text = st.text_input("追加フリーワード", placeholder="例: 穴場スポット", value="")
    
    submit_button = st.form_submit_button(label='🚀 検索スタート', type="primary", use_container_width=True)

# --- 結果処理 ---
if submit_button:
    final_query = f"{default_text} {additional_text}".strip()
    
    if not final_query:
        st.warning("タグを選ぶか、キーワードを入力してください")
    else:
        with st.spinner('AIがプランを作成中...'):
            try:
                prompt = f"""
                テーマ: {final_query}
                スタイル: {style}
                東京の撮影スポットを5つ提案。
                JSON形式:
                name, search_name(GoogleMap用), area, reason, permission(許可目安), 
                video_idea(構成案), script(短い脚本), fashion(服装), bgm(音楽), sns_info, lat, lon
                """

                response = model.generate_content(prompt)
                
                text_resp = response.text.strip()
                if text_resp.startswith("```json"): text_resp = text_resp[7:-3]
                elif text_resp.startswith("```"): text_resp = text_resp[3:-3]
                
                spots = json.loads(text_resp)
                
                st.success(f"🔍 検索完了: {final_query}")
                
                df = pd.DataFrame(spots)
                st.map(df, latitude='lat', longitude='lon', size=20, color='#FF4B4B')

                for spot in spots:
                    with st.expander(f"📍 {spot['name']}", expanded=False):
                        perm = spot['permission']
                        if "禁止" in perm or "許可" in perm: st.error(f"⚠️ {perm}")
                        else: st.caption(f"ℹ️ {perm}")

                        t1, t2, t3 = st.tabs(["🎥 構成", "👗 衣装/SNS", "🗺️ 行く"])
                        with t1:
                            st.markdown(f"**Point:** {spot['reason']}")
                            st.info(f"**構成:** {spot['video_idea']}")
                            st.code(spot['script'], language="text")
                        with t2:
                            st.markdown(f"**👗:** {spot['fashion']}")
                            st.markdown(f"**🎵:** {spot['bgm']}")
                            st.code(spot['sns_info'], language="text")
                        with t3:
                            q = spot['search_name'].replace(" ", "+")
                            st.link_button("📍 Googleマップ", f"https://www.google.com/maps/search/?api=1&query={q}", use_container_width=True)
                            st.link_button("🚶‍♂️ ナビ開始", f"https://www.google.com/maps/dir/?api=1&destination={q}", use_container_width=True)

            except Exception as e:
                st.error("エラーが発生しました。")
                st.caption(str(e))