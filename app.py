import streamlit as st
import google.generativeai as genai
import os
import json
import pandas as pd
from dotenv import load_dotenv

# --- 設定の読み込み ---
# ローカル開発用（.envファイルがある場合）
load_dotenv()

# --- ページ設定 ---
st.set_page_config(page_title="東京動画ネタ帳 Ultimate Studio", layout="wide")

# ==========================================
# 🔐 簡易ログイン機能 (ここを追加)
# ==========================================
def check_password():
    """パスワードが合っているか確認する関数"""
    # 1. セッション状態にログインフラグがなければFalseにする
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    # 2. すでにログイン済みなら何もしない
    if st.session_state['logged_in']:
        return True

    # 3. ログイン画面の表示
    st.header("🔒 ログイン")
    st.write("このアプリは関係者専用です。パスワードを入力してください。")
    
    password = st.text_input("パスワード", type="password")
    
    # 4. パスワード照合
    # Streamlit CloudのSecrets機能、または環境変数から正解パスワードを取得
    # 設定がない場合のデフォルトは 'admin123' (本番では必ず変更してください)
    correct_password = os.getenv("APP_PASSWORD") or st.secrets.get("APP_PASSWORD") or "admin123"

    if st.button("ログイン"):
        if password == correct_password:
            st.session_state['logged_in'] = True
            st.rerun() # 画面を再読み込みしてアプリを表示
        else:
            st.error("パスワードが違います")
    
    return False

# パスワードチェック実行。ログインしていなければここで処理を止める（アプリの中身を見せない）
if not check_password():
    st.stop()

# ==========================================
# 以下、ログイン成功後のアプリ本体
# ==========================================

# --- APIキーの取得優先順位: 1.Secrets(クラウド) 2.環境変数(.env) ---
# Streamlit Cloudでは st.secrets を使うのが一般的です
if "GEMINI_API_KEY" in st.secrets:
    API_KEY = st.secrets["GEMINI_API_KEY"]
else:
    API_KEY = os.getenv("GEMINI_API_KEY")

# --- Gemini APIの設定 ---
if not API_KEY:
    st.error("APIキーが設定されていません。")
    st.stop()

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# --- セッション状態の初期化 ---
if 'search_query' not in st.session_state:
    st.session_state['search_query'] = ""

def set_query(text):
    st.session_state['search_query'] = text

# --- UIヘッダー ---
st.title("🎬 東京動画ネタ帳: Ultimate Studio")
st.markdown("ロケ地、脚本、そして**「衣装・BGM・ハッシュタグ」**まで。AIがトータルプロデュースします。")

# --- 🎨 ビジュアルスタンプエリア ---
st.markdown("### 1. 撮りたい画から選ぶ")

tab1, tab2, tab3 = st.tabs(["🕒 時間帯・天気", "✨ 雰囲気・感情", "🏙️ 場所・建物"])

with tab1:
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("🌅 早朝の静寂", use_container_width=True): set_query("人がいない早朝の東京、朝日が差し込むビル街や公園、澄んだ空気")
    if c2.button("🌇 夕暮れ・マジックアワー", use_container_width=True): set_query("夕日が沈む直前の空、シルエットが美しい場所、オレンジ色の街並み")
    if c3.button("🌃 真夜中の孤独", use_container_width=True): set_query("深夜の誰もいない道路、街灯だけが光る場所、孤独感のある都会")
    if c4.button("☔ 雨の日のリフレクション", use_container_width=True): set_query("雨で濡れた地面にネオンが反射する場所、ガラス越しの雨粒")

with tab2:
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("☕ チル・落ち着く", use_container_width=True): set_query("風の音が聞こえるような静かな場所、緑とベンチがある場所、リラックスできる風景")
    if c2.button("🎞️ ノスタルジック", use_container_width=True): set_query("昭和レトロな路地裏、錆びた看板、時間が止まったような懐かしい場所")
    if c3.button("🤖 サイバーパンク", use_container_width=True): set_query("近未来的な構造物、複雑なパイプや電線、LEDの光、ブレードランナーのような雰囲気")
    if c4.button("🍃 廃墟・退廃美", use_container_width=True): set_query("植物に侵食された人工物、古びたコンクリート、少し不気味だが美しい場所")

with tab3:
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("⛩️ 神社・仏閣", use_container_width=True): set_query("静寂に包まれた境内、木漏れ日、石畳、日本的な美しさ")
    if c2.button("🏭 工場・インダストリアル", use_container_width=True): set_query("巨大な鉄骨、煙突、メカニカルな構造美、夜の工場地帯")
    if c3.button("🌉 橋・水辺", use_container_width=True): set_query("川沿いの遊歩道、巨大な橋の下、水面に映る街の光")
    if c4.button("🚈 電車・高架下", use_container_width=True): set_query("電車の通過音が響く高架下、線路沿いの小道、踏切のある風景")

# --- 検索フォーム ---
st.markdown("---")
st.markdown("### 2. 撮影スタイルとテーマを決める")

with st.form(key='search_form'):
    # 人数・スタイル選択
    style = st.radio(
        "撮影人数・スタイル",
        ["👤 一人で撮影 (Vlog・自撮り・風景)", "👥 複数人で撮影 (演者あり・会話劇・デート風)"],
        horizontal=True
    )
    
    theme = st.text_input("検索テーマ（スタンプを押すと自動入力）", value=st.session_state['search_query'])
    submit_button = st.form_submit_button(label='🚀 トータルプランを作成')

# --- 処理実行 ---
if submit_button and theme:
    st.session_state['search_query'] = theme
    
    with st.spinner('ロケ地、脚本、衣装、音楽、SNS戦略を構築中...'):
        try:
            # プロンプト
            prompt = f"""
            ユーザーのテーマ「{theme}」に基づき、東京の撮影スポットを5つ提案してください。
            【現在の撮影スタイル】: {style}
            【必須要件】
            1. lat/lon: アプリ内地図用（必須）。
            2. search_name: Googleマップ検索用の正確な名称。
            3. permission: 撮影許可の目安。
            4. video_idea: カメラワークや構図の提案。
            5. script: {style} に合わせた短い脚本・演出指示。
            6. fashion: その場所の雰囲気に合うおすすめの服装・ファッション。
            7. bgm: 編集時に合わせるべきBGMのジャンルや雰囲気。
            8. sns_tags: TikTok/Reels投稿用のバズりそうなハッシュタグ5〜6個と、キャッチーなタイトル案。

            以下のJSONフォーマットのみを返してください。
            [
                {{
                    "name": "スポット名",
                    "search_name": "Googleマップ検索用の正確な名称",
                    "area": "エリア名",
                    "reason": "撮影ポイント解説",
                    "permission": "⚠️ 許可・注意点の目安",
                    "video_idea": "🎥 カメラワーク案",
                    "script": "📝 脚本・セリフ・演出指示",
                    "fashion": "👗 おすすめファッション",
                    "bgm": "🎵 推奨BGM",
                    "sns_info": "📱 SNSタイトル案とハッシュタグ",
                    "lat": 35.xxxxxx,
                    "lon": 139.xxxxxx
                }}
            ]
            """

            response = model.generate_content(prompt)
            
            text_response = response.text.strip()
            if text_response.startswith("```json"):
                text_response = text_response[7:-3]
            elif text_response.startswith("```"):
                text_response = text_response[3:-3]
            
            spots = json.loads(text_response)

            st.success(f"📍 「{theme}」の撮影プラン")
            df = pd.DataFrame(spots)
            st.map(df, latitude='lat', longitude='lon', size=20, color='#FF4B4B')

            st.markdown("### 📋 撮影＆演出指示書")
            for spot in spots:
                with st.expander(f"📍 {spot['name']} （{spot['area']}）", expanded=True):
                    perm_text = spot['permission']
                    if "禁止" in perm_text or "許可" in perm_text or "私有地" in perm_text:
                        st.error(f"**{perm_text}**")
                    else:
                        st.warning(f"**{perm_text}**")

                    c1, c2, c3 = st.columns([1.2, 1.2, 0.6])
                    
                    with c1:
                        st.markdown(f"**💬 ポイント:** {spot['reason']}")
                        st.info(f"**🎥 構成案:**\n{spot['video_idea']}")
                        st.markdown("---")
                        st.markdown(f"**👗 服装:** {spot['fashion']}")
                        st.markdown(f"**🎵 BGM:** {spot['bgm']}")
                    
                    with c2:
                        st.markdown("#### 📝 Scenario")
                        st.code(spot['script'], language="text")
                        st.markdown("#### 📱 SNS Posting")
                        st.code(spot['sns_info'], language="text")
                    
                    with c3:
                        map_query = spot['search_name'].replace(" ", "+")
                        google_map_url = f"https://www.google.com/maps/search/?api=1&query={map_query}"
                        dir_url = f"https://www.google.com/maps/dir/?api=1&destination={map_query}"
                        
                        st.link_button("📍 マップ保存", google_map_url, type="primary", use_container_width=True)
                        st.link_button("🚶‍♂️ 経路案内", dir_url, use_container_width=True)
                        
                        img_search_url = f"https://www.google.com/search?q={map_query}+風景&tbm=isch"
                        st.markdown(f"[🖼️ 参考写真]({img_search_url})")

        except Exception as e:
            st.error(f"エラーが発生しました: {e}")
            st.info("もう一度ボタンを押してみてください。")

elif submit_button and not theme:
    st.warning("スタンプを選ぶか、テーマを入力してください。")