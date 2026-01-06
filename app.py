import streamlit as st
import google.generativeai as genai
import os
import json
import pandas as pd
from dotenv import load_dotenv

# --- 設定の読み込み ---
load_dotenv()

# --- ページ設定 ---
st.set_page_config(page_title="東京動画ネタ帳 Ultimate", layout="wide")

# ==========================================
# 🎨 デザイン調整 (CSS注入)
# ==========================================
st.markdown("""
    <style>
    /* 1. 上部のバー（ヘッダー）とフッターを消す */
    [data-testid="stHeader"] {
        display: none;
    }
    footer {
        visibility: hidden;
    }
    
    /* 2. スマホ向け: 全体の余白をギュッと詰める */
    .block-container {
        padding-top: 1rem;     /* 上の隙間をなくす */
        padding-bottom: 5rem;  /* 下はスクロール用に少し空ける */
        padding-left: 0.5rem;  /* 横の隙間も最小限に */
        padding-right: 0.5rem;
    }
    
    /* 3. ボタンをスマホで押しやすく（高さを出して太字に） */
    .stButton button {
        min-height: 50px;
        font-weight: bold;
        border-radius: 12px; /* 角丸でアプリっぽく */
    }

    /* 4. タブの文字を大きく */
    button[data-baseweb="tab"] {
        font-size: 16px;
        padding: 10px;
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

    st.header("🔒 ログイン")
    password = st.text_input("パスワード", type="password")
    
    # Secretsまたは環境変数からパスワード取得
    correct_password = os.getenv("APP_PASSWORD") or st.secrets.get("APP_PASSWORD") or "admin123"

    if st.button("ログイン", use_container_width=True):
        if password == correct_password:
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

# APIキー取得
if "GEMINI_API_KEY" in st.secrets:
    API_KEY = st.secrets["GEMINI_API_KEY"]
else:
    API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    st.error("APIキー設定エラー")
    st.stop()

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# セッション初期化
if 'search_query' not in st.session_state:
    st.session_state['search_query'] = ""

def set_query(text):
    st.session_state['search_query'] = text

# タイトル（スマホでも見やすく短縮）
st.title("🎬 Tokyo Location Guide")
st.caption("AIがロケ地・脚本・衣装・タグを完全プロデュース")

# --- スタンプエリア ---
st.markdown("### 1. イメージ選択")

tab1, tab2, tab3 = st.tabs(["🕒 時間/天気", "✨ 雰囲気", "🏙️ 場所"])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🌅 早朝", use_container_width=True): set_query("早朝の東京、朝日、静寂、澄んだ空気")
        if st.button("🌃 深夜", use_container_width=True): set_query("深夜の道路、街灯、孤独感、誰もいない都会")
    with c2:
        if st.button("🌇 夕暮れ", use_container_width=True): set_query("夕焼け、マジックアワー、シルエット、オレンジ色の空")
        if st.button("☔ 雨の日", use_container_width=True): set_query("雨の路面反射、ガラス越しの雨粒、ネオン、濡れた質感")

with tab2:
    c1, c2 = st.columns(2)
    with c1:
        if st.button("☕ チル", use_container_width=True): set_query("風の音、緑とベンチ、リラックス、静かな公園")
        if st.button("🤖 近未来", use_container_width=True): set_query("サイバーパンク、LED、電線、ブレードランナー風")
    with c2:
        if st.button("🎞️ レトロ", use_container_width=True): set_query("昭和レトロ、路地裏、錆びた看板、ノスタルジー")
        if st.button("🍃 廃墟感", use_container_width=True): set_query("植物に侵食された壁、古びたコンクリート、退廃美")

with tab3:
    c1, c2 = st.columns(2)
    with c1:
        if st.button("⛩️ 神社", use_container_width=True): set_query("静寂な境内、石畳、木漏れ日、和の雰囲気")
        if st.button("🌉 水辺", use_container_width=True): set_query("川沿いの遊歩道、橋の下、水面反射")
    with c2:
        if st.button("🏭 工場", use_container_width=True): set_query("鉄骨、パイプ、インダストリアル、夜の工場")
        if st.button("🚈 電車", use_container_width=True): set_query("高架下、線路沿い、踏切、電車の通過音")

# --- 入力エリア ---
st.markdown("---")
st.markdown("### 2. スタイル設定")

with st.form(key='search_form'):
    style = st.radio(
        "人数",
        ["👤 一人 (Vlog/風景)", "👥 複数 (会話劇/MV)"],
        horizontal=True
    )
    
    theme = st.text_input("テーマ (自動入力)", value=st.session_state['search_query'])
    
    # スマホで一番目立つようにメインボタンを配置
    submit_button = st.form_submit_button(label='🚀 プランを作成する', type="primary", use_container_width=True)

# --- 結果表示 ---
if submit_button and theme:
    st.session_state['search_query'] = theme
    
    with st.spinner('AIプロデューサーが思考中...'):
        try:
            prompt = f"""
            ユーザーのテーマ「{theme}」に基づき、東京の撮影スポットを5つ提案してください。
            スタイル: {style}
            
            JSON形式で以下を含めてください:
            name, search_name(GoogleMap用), area, reason, permission(許可目安), 
            video_idea(構成案), script(短い脚本), fashion(服装), bgm(音楽), 
            sns_info(タグとタイトル), lat, lon
            """

            response = model.generate_content(prompt)
            
            # JSONクリーニング処理
            text_response = response.text.strip()
            if text_response.startswith("```json"):
                text_response = text_response[7:-3]
            elif text_response.startswith("```"):
                text_response = text_response[3:-3]
            
            spots = json.loads(text_response)

            st.success("✅ プラン作成完了")
            
            # 地図
            df = pd.DataFrame(spots)
            st.map(df, latitude='lat', longitude='lon', size=20, color='#FF4B4B')

            # 詳細カード
            for spot in spots:
                with st.expander(f"📍 {spot['name']}", expanded=False):
                    
                    # 許可アラート
                    perm = spot['permission']
                    if "禁止" in perm or "許可" in perm:
                        st.error(f"⚠️ {perm}")
                    else:
                        st.caption(f"ℹ️ {perm}")

                    # タブで情報を整理（スマホで見やすく）
                    t1, t2, t3 = st.tabs(["🎥 構成・演出", "👗 衣装・SNS", "🗺️ マップ"])
                    
                    with t1:
                        st.markdown(f"**Point:** {spot['reason']}")
                        st.info(f"**構成:** {spot['video_idea']}")
                        st.markdown("**📝 脚本:**")
                        st.code(spot['script'], language="text")

                    with t2:
                        st.markdown(f"**👗:** {spot['fashion']}")
                        st.markdown(f"**🎵:** {spot['bgm']}")
                        st.markdown("**📱 SNS:**")
                        st.code(spot['sns_info'], language="text")

                    with t3:
                        q = spot['search_name'].replace(" ", "+")
                        map_url = f"https://www.google.com/maps/search/?api=1&query={q}"
                        dir_url = f"https://www.google.com/maps/dir/?api=1&destination={q}"
                        
                        st.link_button("📍 Googleマップを開く", map_url, type="primary", use_container_width=True)
                        st.link_button("🚶‍♂️ ここへ行く（ナビ）", dir_url, use_container_width=True)

        except Exception as e:
            st.error("エラーが発生しました。もう一度お試しください。")
            st.caption(f"Error: {e}")

elif submit_button and not theme:
    st.warning("テーマを入力してください")