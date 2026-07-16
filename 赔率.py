import streamlit as st
import pandas as pd
import requests

# ================= 配置页面 =================
st.set_page_config(page_title="全球赛事实时赔率监控中心", layout="wide")
st.title("🌐 全球赛事实时赔率监控中心 (Prototype)")
st.markdown("对接全球真实博彩公司数据接口，实时监控水位波动，辅助量化决策。")

# ================= 配置 API =================
# ⚠️ 注意：在这里填入你申请的免费 API Key
API_KEY = 'f57a64cbf23b946e6e533dcc4bc1fabf' 

# 赛事键值字典 
SPORT_KEYS = {
    "🏆 足球 - 2026 世界杯": "soccer_fifa_world_cup",
    "⚽️ 足球 - 英超 (EPL)": "soccer_epl",
    "🏀 篮球 - NBA": "basketball_nba",
    "⚽️ 足球 - 西甲": "soccer_spain_la_liga"
}

# ================= 核心抓取逻辑 =================
@st.cache_data(ttl=60) # 缓存 60 秒，保护免费额度
def fetch_all_matches(sport_key):
    """抓取选定联赛下的所有即将进行的比赛"""
    if API_KEY == 'YOUR_API_KEY_HERE':
        return None, "请先在代码中填入真实的 API Key"

    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={API_KEY}&regions=uk,eu,us&markets=h2h"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        if not data:
            return [], "当前该联赛处于休赛期或暂无比赛"
            
        return data, "success"
        
    except requests.exceptions.RequestException as e:
        return None, f"API 请求失败: {e}"

def parse_match_data(match_data):
    """解析单场比赛中各大博彩公司的赔率"""
    parsed_data = []
    for bookmaker in match_data['bookmakers']:
        company_name = bookmaker['title']
        h2h_market = next((m for m in bookmaker['markets'] if m['key'] == 'h2h'), None)
        
        if h2h_market:
            odds_dict = {'Company': company_name}
            for outcome in h2h_market['outcomes']:
                team_name = outcome['name']
                odds_dict[team_name] = outcome['price']
            parsed_data.append(odds_dict)
            
    return pd.DataFrame(parsed_data)

# ================= 侧边栏与 UI =================
st.sidebar.header("⚙️ 监控设置")
selected_sport = st.sidebar.selectbox("1. 选择监控联赛", list(SPORT_KEYS.keys()))
sport_key = SPORT_KEYS[selected_sport]

# 获取该联赛所有比赛数据
all_matches, status_msg = fetch_all_matches(sport_key)

if all_matches is None:
    st.error(f"⚠️ {status_msg}")
    st.markdown("👉 **请前往 [The Odds API](https://the-odds-api.com/) 获取 额外API Key**")
elif not all_matches:
    st.sidebar.warning(f"⚠️ {status_msg}")
    st.warning("当前所选联赛暂无比赛数据，请切换其他联赛（推荐测试：2026 世界杯）。")
else:
    # 提取所有比赛的名称，生成第二个下拉菜单
    match_options = {f"{m['home_team']} vs {m['away_team']}": m for m in all_matches}
    selected_match_name = st.sidebar.selectbox("2. 选择具体赛事", list(match_options.keys()))
    
    # 获取用户选中比赛的详细数据
    target_match_data = match_options[selected_match_name]
    
    st.subheader(f"当前锁定赛事: **{selected_match_name}**")
    
    df_odds = parse_match_data(target_match_data)
    
    if df_odds.empty:
        st.warning("这场比赛暂无各大博彩公司的赔率数据。")
    else:
        teams = [col for col in df_odds.columns if col != 'Company']
        
        # 计算并展示平均赔率卡片
        st.markdown("全网平均赔率 (Average Odds)")
        cols = st.columns(len(teams))
        for i, team in enumerate(teams):
            avg_odd = round(df_odds[team].mean(), 2)
            cols[i].metric(label=f"[{team}] 平均水位", value=avg_odd)

        st.divider()

        # 展示各大公司的原始数据对比
        st.markdown("各大庄家实时原始水位一览")
        st.dataframe(df_odds, use_container_width=True, hide_index=True)
        
        # 添加刷新按钮
        if st.button("🔄 手动获取最新全网赔率"):
            fetch_all_matches.clear() # 清除缓存，强制去 API 拉取最新数据
            st.rerun()