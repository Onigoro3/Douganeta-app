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
# 🎨 デザイン調整 (スマホ最適化 + バケツ表示)
# ==========================================
st.markdown("""
    <style>
    /* ヘッダー削除 */
    header[data-testid="stHeader"], footer {display: none !important;}
    
    /* スマホ向け余白調整 */
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
        height: 3rem !important;
        font-weight: bold !important;
    }
    
    /* バケツ（選択タグ）エリアのデザイン */
    .tag-container {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 10px;
        margin-bottom: 15px;
        border: 1px solid #ddd;
    }
    .selected-tag {
        display: inline-block;
        background-color: #FF4B4B;
        color: white;
        padding: 5px 10px;
        margin: 3px;
        border-radius: 15px;
        font-size: 0.9rem;
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

# API設定
if "GEMINI_API_KEY" in st.secrets:
    API_KEY = st.secrets["GEMINI_API_KEY"]
else:
    API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    st.error("APIキー設定エラー")
    st.stop()

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# --- バケツ（選択タグ）の管理 ---
if 'selected_tags' not in st.session_state:
    st.session_state['selected_tags'] = []

def add_tag(tag_text):
    """タグをバケツに追加する（重複なし）"""
    if tag_text not in st.session_state['selected_tags']:
        st.session_state['selected_tags'].append(tag_text)

def clear_tags():
    """バケツを空にする"""
    st.session_state['selected_tags'] = []

# --- タイトル ---
st.markdown("### 🎬 Tokyo Video Planner")

# --- 🛒 バケツ（選択された要素の表示エリア） ---
st.markdown("##### 🛒 選択中の要素 (Bucket)")

# タグ表示エリア
if st.session_state['selected_tags']:
    tags_html = ""
    for tag in st.session_state['selected_tags']:
        tags_html += f'<span class="selected-tag">{tag}</span>'
    st.markdown(f'<div class="tag-container">{tags_html}</div>', unsafe_allow_html=True)
    
    # クリアボタン
    if st.button("🗑️ 選択をリセット", use_container_width=True):
        clear_tags()
        st.rerun()
else:
    st.info("下のボタンを押すとここに追加されます")

# --- スタンプ選択エリア ---
st.markdown("---")
tab1, tab2, tab3 = st.tabs(["✨ Atmosphere (雰囲気)", "📍 Location (場所)", "🕒 Time (時間)"])

# 1. Atmosphere (雰囲気)
with tab1:
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🎞️ ノスタルジック"): add_tag("ノスタルジック・昭和レトロ")
        if st.button("☕ チル・リラックス"): add_tag("静か・チル・落ち着く")
        if st.button("🍃 廃墟・退廃的"): add_tag("廃墟感・退廃美")
    with c2:
        if st.button("🤖 サイバーパンク"): add_tag("サイバーパンク・近未来")
        if st.button("💎 ラグジュアリー"): add_tag("高級感・ラグジュアリー・都会的")
        if st.button("⚡ エネルギッシュ"): add_tag("雑踏・活気・エネルギッシュ")

# 2. Location (場所)
with tab2:
    c1, c2 = st.columns(2)
    with c1:
        if st.button("⛩️ 神社・仏閣"): add_tag("神社・寺院・和風建築")
        if st.button("🌉 海・水辺"): add_tag("海・川・水辺・橋")
        if st.button("🌳 公園・自然"): add_tag("公園・森林・自然")
    with c2:
        if st.button("🏙️ ビル街・屋上"): add_tag("高層ビル・屋上・展望台")
        if st.button("🛤️ 路地裏・横丁"): add_tag("路地裏・飲み屋街・横丁")
        if st.button("🏭 工場・インダストリアル"): add_tag("工場・倉庫・鉄骨")

# 3. Time (時間・天気)
with tab3:
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🌅 早朝"): add_tag("早朝・朝焼け・無人")
        if st.button("🌇 夕暮れ"): add_tag("夕暮れ・マジックアワー")
    with c2:
        if st.button("🌃 深夜"): add_tag("深夜・夜景・暗闇")
        if st.button("☔ 雨の日"): add_tag("雨・リフレクション・傘")

# --- 検索実行フォーム ---
st.markdown("---")
with st.form(key='search_form'):
    style = st.radio("スタイル", ["👤 一人 (Vlog)", "👥 複数 (会話劇)"], horizontal=True)
    
    # バケツの中身を自動入力値として使う
    default_text = " ".join(st.session_state['selected_tags'])
    additional_text = st.text_input("追加キーワード (自由入力)", placeholder="例: 人が少ない場所")
    
    submit_button = st.form_submit_button(label='🚀 この組み合わせで探す', type="primary", use_container_width=True)

# --- 結果処理 ---
if submit_button:
    # 検索ワードの結合
    final_query = f"{default_text} {additional_text}".strip()
    
    if not final_query:
        st.warning("タグを選ぶか、キーワードを入力してください")
    else:
        with st.spinner('AIが最適な組み合わせを検索中...'):
            try:
                prompt = f"""
                テーマ: {final_query}
                スタイル: {style}
                
                東京の撮影スポットを5つ提案してください。
                JSON形式:
                name, search_name(GoogleMap用), area, reason(選定理由), permission(許可目安), 
                video_idea(構成案), script(短い脚本), fashion(服装), bgm(音楽), sns_info, lat, lon
                """

                response = model.generate_content(prompt)
                
                # JSONクリーニング
                text_resp = response.text.strip()
                if text_resp.startswith("```json"): text_resp = text_resp[7:-3]
                elif text_resp.startswith("```"): text_resp = text_resp[3:-3]
                
                spots = json.loads(text_resp)
                
                st.success(f"🔍 「{final_query}」のプラン")
                
                # マップ表示
                df = pd.DataFrame(spots)
                st.map(df, latitude='lat', longitude='lon', size=20, color='#FF4B4B')

                # カード表示
                for spot in spots:
                    with st.expander(f"📍 {spot['name']}", expanded=False):
                        # 許可情報
                        perm = spot['permission']
                        if "禁止" in perm or "許可" in perm: st.error(f"⚠️ {perm}")
                        else: st.caption(f"ℹ️ {perm}")

                        # 詳細タブ
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