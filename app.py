import streamlit as st
import google.generativeai as genai
import os
import json
import pandas as pd
from dotenv import load_dotenv

# --- 設定の読み込み ---
load_dotenv()

# --- ページ設定 ---
st.set_page_config(page_title="Japan Video Planner", layout="wide", initial_sidebar_state="collapsed")

# ==========================================
# 🎨 デザイン調整 (スマホ横並び対応版)
# ==========================================
st.markdown("""
    <style>
    /* ヘッダー削除 */
    header[data-testid="stHeader"], footer {display: none !important;}
    
    /* スマホ向け全体余白調整 */
    .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 5rem !important;
        padding-left: 0.2rem !important;
        padding-right: 0.2rem !important;
    }
    
    /* ★重要: スマホでもカラムを横並びにする強制CSS ★ */
    @media (max-width: 640px) {
        div[data-testid="column"] {
            width: 33% !important; /* 3列強制 */
            flex: 0 0 33% !important;
            min-width: 0 !important;
            padding: 0 2px !important; /* 隙間を詰める */
        }
        /* ボタン内の文字を小さくして改行を防ぐ */
        .stButton > button {
            font-size: 10px !important;
            padding: 2px !important;
            min-height: 45px !important;
            height: 45px !important;
        }
        /* スタンプエリアの列調整が全体に影響しないよう、入力フォームなどは戻す */
        div[data-testid="stForm"] div[data-testid="column"] {
            width: 100% !important;
            flex: 1 1 100% !important;
        }
    }

    /* ボタンデザイン (視認性確保) */
    .stButton > button {
        width: 100% !important;
        border-radius: 8px !important;
        min-height: 3rem;
        height: auto;
        padding: 4px !important;
        font-weight: bold !important;
        line-height: 1.1 !important;
        white-space: normal !important; /* 折り返し許可 */
        
        /* 配色強制指定 */
        background-color: #ffffff !important;
        color: #262730 !important;
        border: 1px solid #d0d7de !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    
    /* 押した感が出るようにホバー設定 */
    .stButton > button:active, .stButton > button:focus:not(:active) {
        background-color: #FF4B4B !important;
        color: #ffffff !important;
        border-color: #FF4B4B !important;
    }

    /* バケツ（選択タグ）のデザイン */
    .tag-container {
        background-color: #ffffff;
        padding: 8px;
        border-radius: 8px;
        margin-bottom: 5px;
        border: 2px solid #FF4B4B;
        text-align: center;
        min-height: 40px;
        color: #333;
    }
    
    .selected-tag {
        display: inline-block;
        background-color: #FF4B4B;
        color: white !important;
        padding: 4px 8px;
        margin: 2px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: bold;
    }
    
    /* タブ調整 */
    button[data-baseweb="tab"] {
        font-size: 12px !important;
        padding: 5px !important;
        font-weight: bold !important;
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

# --- グリッド生成関数 (スマホ横並び対応) ---
def create_grid(items, cols=3):
    # CSSで強制的に並べるため、st.columnsを使用
    for i in range(0, len(items), cols):
        columns = st.columns(cols)
        for j, col in enumerate(columns):
            if i + j < len(items):
                label, val = items[i + j]
                if col.button(label, key=f"btn_{val}_{i}_{j}", use_container_width=True):
                    add_tag(val)

# --- タイトル ---
st.markdown("<h4 style='text-align: center; margin:0;'>🇯🇵 Video Planner</h4>", unsafe_allow_html=True)

# --- 🛒 バケツ表示 ---
if st.session_state['selected_tags']:
    tags_html = ""
    for tag in st.session_state['selected_tags']:
        tags_html += f'<span class="selected-tag">{tag}</span>'
    st.markdown(f'<div class="tag-container">{tags_html}</div>', unsafe_allow_html=True)
    
    if st.button("🗑️ リセット", use_container_width=True):
        clear_tags()
        st.rerun()
else:
    st.markdown("<div class='tag-container' style='color:#999; font-size:12px; padding-top:10px;'>スタンプを押すとここに追加されます</div>", unsafe_allow_html=True)

# --- スタンプ選択エリア ---
tab1, tab2, tab3 = st.tabs(["✨ 雰囲気", "📍 ロケ地", "🕒 時間/天気"])

with tab1:
    # 1行3つで作成（スマホCSSでこれを維持）
    items_atm = [
        ("🎞️ レトロ", "昭和レトロ"), ("🏠 ノスタルジー", "ノスタルジック"), ("☕ チル", "チル"),
        ("🤫 静寂", "静か"), ("😌 リラックス", "落ち着く"), ("🍃 廃墟感", "廃墟"),
        ("🥀 退廃美", "退廃的"), ("🤖 サイバー", "サイバーパンク"), ("🚀 近未来", "SF"),
        ("🏙️ 都会的", "都会的"), ("💎 高級感", "ラグジュアリー"), ("⚡ 活気", "エネルギッシュ"),
        ("👥 雑踏", "人混み"), ("🌸 儚い", "儚い"), ("🎨 映え", "カラフル"),
        ("🎥 シネマ", "映画風"), ("🖤 無機質", "無機質"), ("👻 不気味", "不気味")
    ]
    create_grid(items_atm, cols=3)

with tab2:
    items_loc = [
        ("⛩️ 神社", "神社"), ("🏯 寺院", "寺院"), ("🇯🇵 和風", "和風建築"),
        ("🌉 橋", "橋"), ("🌊 海", "海"), ("🛶 川", "川"),
        ("🚢 港", "港"), ("🌳 公園", "公園"), ("🌲 森林", "森林"),
        ("🌿 緑", "自然"), ("🏙️ ビル", "高層ビル"), ("🏢 屋上", "屋上"),
        ("🔭 展望台", "展望台"), ("🛤️ 路地裏", "路地裏"), ("🏮 横丁", "飲み屋街"),
        ("🏭 工場", "工場"), ("📦 倉庫", "倉庫"), ("⚙️ 鉄骨", "鉄骨"),
        ("🛍️ 商店街", "商店街"), ("🏛️ 建築", "有名建築"), ("🚉 駅", "駅構内"),
        ("🚇 地下", "地下通路"), ("♨️ 温泉", "温泉街"), ("🌾 田舎", "田園")
    ]
    create_grid(items_loc, cols=3)

with tab3:
    items_time = [
        ("🌅 早朝", "早朝"), ("🚷 無人", "無人"), ("🌞 昼間", "昼間"),
        ("🔵 青空", "青空"), ("🌇 夕方", "夕暮れ"), ("🧡 マジック", "マジックアワー"),
        ("🌃 深夜", "深夜"), ("🌑 暗闇", "暗闇"), ("✨ 夜景", "夜景"),
        ("💡 ネオン", "ネオン"), ("☔ 雨", "雨"), ("💧 反射", "リフレクション"),
        ("☁️ 曇り", "曇り"), ("🌸 春/桜", "桜"), ("🍂 秋/紅葉", "紅葉"),
        ("❄️ 冬/雪", "雪")
    ]
    create_grid(items_time, cols=3)

# --- 検索実行フォーム ---
st.markdown("---")
st.markdown("##### 📍 条件指定")

with st.form(key='search_form'):
    col_area, col_style = st.columns([1, 1])
    with col_area:
        target_area = st.text_input("エリア (空欄=全国)", placeholder="例: 京都")
    with col_style:
        style = st.radio("スタイル", ["👤 一人", "👥 複数"])
    
    default_text = " ".join(st.session_state['selected_tags'])
    additional_text = st.text_input("キーワード", placeholder="例: 穴場", value="")
    
    st.markdown("<br>", unsafe_allow_html=True)
    submit_button = st.form_submit_button(label='🇯🇵 検索スタート', type="primary", use_container_width=True)

# --- 結果処理 ---
if submit_button:
    area_query = target_area if target_area else "日本国内"
    final_query = f"{default_text} {additional_text}".strip()
    
    if not final_query and not target_area:
        st.warning("タグかエリアを入力してください")
    else:
        with st.spinner(f'{area_query}で検索中...'):
            try:
                prompt = f"""
                エリア: {area_query}
                条件: {final_query}
                スタイル: {style}
                
                おすすめの動画撮影スポットを5つ提案してください。
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
                
                # 新機能: テキスト保存用のデータ作成
                save_text = f"【撮影プラン】\nエリア: {area_query}\nテーマ: {final_query}\n\n"
                
                df = pd.DataFrame(spots)
                st.map(df, latitude='lat', longitude='lon', size=20, color='#FF4B4B')

                for i, spot in enumerate(spots, 1):
                    # テキスト保存用に追記
                    save_text += f"[{i}] {spot['name']} ({spot['area']})\n"
                    save_text += f"  - ポイント: {spot['reason']}\n"
                    save_text += f"  - 構成案: {spot['video_idea']}\n"
                    save_text += f"  - 脚本: {spot['script']}\n"
                    save_text += f"  - GoogleMap: {spot['search_name']}\n\n"

                    with st.expander(f"📍 {spot['name']}", expanded=False):
                        perm = spot['permission']
                        if "禁止" in perm or "許可" in perm: st.error(f"⚠️ {perm}")
                        else: st.caption(f"ℹ️ {perm}")

                        t1, t2, t3 = st.tabs(["🎥 構成", "👗 衣装", "🗺️ 地図"])
                        with t1:
                            st.info(f"**{spot['video_idea']}**")
                            st.markdown("**脚本:**")
                            st.code(spot['script'], language="text")
                        with t2:
                            st.markdown(f"**👗:** {spot['fashion']}")
                            st.markdown(f"**🎵:** {spot['bgm']}")
                            st.code(spot['sns_info'], language="text")
                        with t3:
                            q = spot['search_name'].replace(" ", "+")
                            st.link_button("📍 Googleマップ", f"https://www.google.com/maps/search/?api=1&query={q}", use_container_width=True)

                # --- 新機能: ダウンロードボタン ---
                st.download_button(
                    label="📥 このプランをテキスト保存",
                    data=save_text,
                    file_name="video_plan.txt",
                    mime="text/plain",
                    use_container_width=True
                )

            except Exception as e:
                st.error("エラーが発生しました。")
                st.caption(str(e))