import streamlit as st
import pandas as pd
import requests

# ================= 配置页面 =================
st.set_page_config(page_title="全球赛事实时赔率监控中心", layout="wide")
st.title("全球赛事实时赔率监控中心 (Ultimate版)")
st.markdown("对接全球真实博彩公司数据接口，支持多盘口玩法切换。**系统严格遵循客观数据源，无开盘数据的选项将留空，杜绝行情造假。**")

API_KEY = 'f57a64cbf23b946e6e533dcc4bc1fabf' 

SPORT_KEYS = {
    "🏆 足球 - 2026 世界杯": "soccer_fifa_world_cup",
    "⚽️ 足球 - 英超 (EPL)": "soccer_epl",
    "🏀 篮球 - NBA": "basketball_nba",
    "⚽️ 足球 - 西甲": "soccer_spain_la_liga"
}

MARKET_KEYS = {
    "独赢盘 (胜平负/1X2)": "h2h",
    "让球盘 (Handicap/Spreads)": "spreads",
    "入球大小 (Over/Under/Totals)": "totals"
}

# ================= 核心抓取逻辑 =================
@st.cache_data(ttl=60) 
def fetch_all_matches(sport_key, market_key):
    if API_KEY == 'YOUR_API_KEY_HERE':
        return None, "请先在代码中填入真实的 API Key"

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
    parsed_data = []
    for bookmaker in match_data['bookmakers']:
        company_name = bookmaker['title']
        target_market = next((m for m in bookmaker['markets'] if m['key'] == market_key), None)
        
        if target_market:
            odds_dict = {'Company': company_name}
            for outcome in target_market['outcomes']:
                col_name = outcome['name']
                if 'point' in outcome:
                    col_name = f"{outcome['name']} [{outcome['point']}]"
                odds_dict[col_name] = outcome['price']
            parsed_data.append(odds_dict)
            
    return pd.DataFrame(parsed_data)

# ================= 侧边栏与 UI =================
st.sidebar.header("监控设置")
selected_sport = st.sidebar.selectbox("1. 选择监控联赛", list(SPORT_KEYS.keys()))
sport_key = SPORT_KEYS[selected_sport]

selected_market = st.sidebar.selectbox("2. 选择盘口玩法", list(MARKET_KEYS.keys()))
market_key = MARKET_KEYS[selected_market]

# 🌟 新增：高阶功能开关
st.sidebar.markdown("---")
st.sidebar.subheader("高阶分析功能")
show_prob = st.sidebar.toggle("开启胜率转换器", value=False)
st.sidebar.caption("开启后，界面水位将转换百分比胜率。")

all_matches, status_msg = fetch_all_matches(sport_key, market_key)

if all_matches is None:
    st.error(f"⚠️ {status_msg}")
elif not all_matches:
    st.sidebar.warning(f"⚠️ {status_msg}")
    st.warning("当前所选联赛暂无比赛数据，请切换其他联赛（推荐测试：2026 世界杯）。")
else:
    match_options = {f"{m['home_team']} vs {m['away_team']}": m for m in all_matches}
    selected_match_name = st.sidebar.selectbox("3. 选择具体赛事", list(match_options.keys()))
    
    target_match_data = match_options[selected_match_name]
    
    st.subheader(f"当前锁定赛事: **{selected_match_name}**")
    st.caption(f"当前分析维度: **{selected_market}**")
    
    df_odds = parse_match_data(target_match_data, market_key)
    
    if df_odds.empty:
        st.warning("这场比赛暂无各大博彩公司针对该玩法的准确开盘数据。")
    else:
        numeric_cols = [col for col in df_odds.columns if col != 'Company']
        
        # ================= 🚨 智能套利监控 (基于确切数据) =================
        st.markdown("智能套利监控引擎")
        
        # 提取每种可能性的全网最高赔率
        max_odds = df_odds[numeric_cols].max()
        # 计算 implied probability 综合
        arbitrage_sum = sum(1 / max_odds.dropna())
        
        if arbitrage_sum < 1.0 and arbitrage_sum > 0:
            profit_margin = (1.0 - arbitrage_sum) * 100
            st.success(f"**发现无风险套利机会！** 跨平台最优组合赔付率低于 100% ({arbitrage_sum*100:.2f}%)。理论无风险利润率: **{profit_margin:.2f}%**")
            
            # 展示最优购买组合
            cols = st.columns(len(numeric_cols))
            for i, col in enumerate(numeric_cols):
                best_company = df_odds.loc[df_odds[col].idxmax(), 'Company']
                best_price = df_odds[col].max()
                cols[i].metric(label=f"买入: {col}", value=f"赔率: {best_price}", delta=f"庄家: {best_company}", delta_color="normal")
        else:
            st.info("当前盘口未发现跨平台无风险套利机会。系统基于客观数据严密监控中...")
        
        st.divider()

        # ================= 📊 数据展示与高亮 =================
        st.markdown("### 🏢 各大庄家实时数据一览")
        
        if show_prob:
            # 开启了胜率转换器：将数字转换为百分比
            df_display = df_odds.copy()
            for col in numeric_cols:
                df_display[col] = df_display[col].apply(lambda x: f"{round(1/x * 100, 2)}%" if pd.notnull(x) else x)
            st.dataframe(df_display, use_container_width=True, hide_index=True)
        else:
            # 原生赔率模式：自动高亮全网最高水位 (浅绿色)
            st.dataframe(
                df_odds.style.highlight_max(subset=numeric_cols, color='#c3f0ca'), 
                use_container_width=True, 
                hide_index=True
            )
        
        if st.button("🔄 手动获取最新全网赔率"):
            fetch_all_matches.clear() 
            st.rerun()
