import streamlit as st
import pandas as pd
import requests

# ================= 配置页面 =================
st.set_page_config(page_title="全球赛事实时赔率监控中心", layout="wide")
st.title("全球赛事实时赔率监控中心 (Prototype)")

# ================= 配置参数 =================
API_KEY = 'f57a64cbf23b946e6e533dcc4bc1fabf' 

SPORT_KEYS = {
    "🏆 足球 - 2026 世界杯": "soccer_fifa_world_cup",
    "⚽️ 足球 - 英超 (EPL)": "soccer_epl",
    "🏀 篮球 - NBA": "basketball_nba",
    "⚽️ 足球 - 西甲": "soccer_spain_la_liga"
}

# 🌟 新增：玩法字典
MARKET_KEYS = {
    "📊 独赢盘 (胜平负/1X2)": "h2h",
    "⚖️ 让球盘 (Handicap/Spreads)": "spreads",
    "⚽ 入球大小 (Over/Under/Totals)": "totals"
}

# ================= 核心抓取逻辑 =================
@st.cache_data(ttl=60) 
def fetch_all_matches(sport_key, market_key):
    """根据选定的联赛和【玩法】抓取数据"""
    if API_KEY == 'YOUR_API_KEY_HERE':
        return None, "请先在代码中填入真实的 API Key"

    # URL 中动态传入用户选择的 market_key (h2h, spreads, 或 totals)
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={API_KEY}&regions=uk,eu,us&markets={market_key}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        if not data:
            return [], "当前该联赛处于休赛期或暂无比赛"
            
        return data, "success"
        
    except requests.exceptions.RequestException as e:
        return None, f"API 请求失败: {e}"

def parse_match_data(match_data, market_key):
    """智能解析不同玩法的客观数据"""
    parsed_data = []
    for bookmaker in match_data['bookmakers']:
        company_name = bookmaker['title']
        target_market = next((m for m in bookmaker['markets'] if m['key'] == market_key), None)
        
        if target_market:
            odds_dict = {'Company': company_name}
            for outcome in target_market['outcomes']:
                # 🌟 核心逻辑：如果是让球或大小球，数据里会包含 'point'（比如 2.5 球，或者 -1.5 球）
                col_name = outcome['name']
                if 'point' in outcome:
                    # 将盘口数值和名称合并，例如 "Over [2.5]"
                    col_name = f"{outcome['name']} [{outcome['point']}]"
                
                odds_dict[col_name] = outcome['price']
            parsed_data.append(odds_dict)
            
    return pd.DataFrame(parsed_data)

# ================= 侧边栏与 UI =================
st.sidebar.header("监控设置")
selected_sport = st.sidebar.selectbox("1. 选择监控联赛", list(SPORT_KEYS.keys()))
sport_key = SPORT_KEYS[selected_sport]

# 🌟 新增：玩法选择器
selected_market = st.sidebar.selectbox("2. 选择盘口玩法", list(MARKET_KEYS.keys()))
market_key = MARKET_KEYS[selected_market]

# 获取数据 (现在受联赛和玩法双重控制)
all_matches, status_msg = fetch_all_matches(sport_key, market_key)

if all_matches is None:
    st.error(f"⚠️ {status_msg}")
elif not all_matches:
    st.sidebar.warning(f"⚠️ {status_msg}")
    st.warning("当前所选联赛暂无比赛数据，请切换其他联赛。")
else:
    match_options = {f"{m['home_team']} vs {m['away_team']}": m for m in all_matches}
    selected_match_name = st.sidebar.selectbox("3. 选择具体赛事", list(match_options.keys()))
    
    target_match_data = match_options[selected_match_name]
    
    st.subheader(f"当前锁定赛事: **{selected_match_name}**")
    st.caption(f"当前分析维度: **{selected_market}**")
    
    # 传入 market_key 进行针对性解析
    df_odds = parse_match_data(target_match_data, market_key)
    
    if df_odds.empty:
        st.warning("这场比赛暂无各大博彩公司针对该玩法的准确开盘数据。")
    else:
        # 展示各大公司的原始数据对比 (存在 NaN 是客观现象，代表该庄家未开此具体点数)
        st.markdown("大庄家实时原始水位一览")
        st.dataframe(df_odds, use_container_width=True, hide_index=True)
        
        if st.button("🔄 手动获取最新全网赔率"):
            fetch_all_matches.clear() 
            st.rerun()
