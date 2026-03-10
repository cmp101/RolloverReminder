import streamlit as st
import yfinance as yf
from datetime import datetime, timedelta
import pandas as pd

# --- 1. 配置页面 ---
st.set_page_config(page_title="期货 FND 全能监控", page_icon="🛡️", layout="wide")

# --- 2. 品种结算属性词典 ---
def get_contract_info(symbol):
    specs = {
        "GC=F": {"name": "黄金", "type": "实物交割"},
        "SI=F": {"name": "白银", "type": "实物交割"},
        "HG=F": {"name": "铜", "type": "实物交割"},
        "CL=F": {"name": "原油(WTI)", "type": "实物交割"},
        "NG=F": {"name": "天然气", "type": "实物交割"},
        "RB=F": {"name": "汽油", "type": "实物交割"},
        "LE=F": {"name": "活牛", "type": "实物交割"},
        "GF=F": {"name": "饲料牛", "type": "现金结算"},
        "HE=F": {"name": "瘦肉猪", "type": "现金结算"},
        "ES=F": {"name": "标普500", "type": "现金结算"},
        "NQ=F": {"name": "纳指100", "type": "现金结算"},
        "MES=F": {"name": "微型标普", "type": "现金结算"},
        "MNQ=F": {"name": "微型纳指", "type": "现金结算"},
    }
    return specs.get(symbol, {"name": "未知", "type": "请核实"})

# --- 3. 自动 FND 计算逻辑 ---
def calculate_auto_fnd(symbol, expiry_date):
    if "LE=F" in symbol:
        return expiry_date.replace(day=1) - timedelta(days=1)
    elif any(x in symbol for x in ["GC=F", "SI=F"]):
        return expiry_date - timedelta(days=25)
    elif "CL=F" in symbol:
        return expiry_date - timedelta(days=3)
    elif any(x in symbol for x in ["GF=F", "ES=F", "NQ=F", "MES=F", "MNQ=F", "HE=F"]):
        return expiry_date
    else:
        return expiry_date - timedelta(days=2)

# --- 4. 侧边栏设计 ---
st.sidebar.header("⚙️ 持仓与修正设置")
with st.sidebar.form("futures_master_form"):
    # 待监控的品种列表
    raw_input = st.text_area("1. 监控品种 (逗号分隔)", "GC=F, CL=F, GF=F, LE=F")
    
    st.sidebar.write("---")
    #st.sidebar.subheader("2. 批量手动修正 (可选)")
    # 允许输入多个品种的修正，格式为 代码:YYYY-MM-DD
    manual_input = st.text_area(
        "输入格式: 代码:日期 (逗号分隔)", 
        value="", 
        placeholder="例如: GC=F:2026-03-25, CL=F:2026-03-22",
        help="不填则使用系统预估"
    )
    
    submit_button = st.form_submit_button(" 确认并刷新")

# --- 5. 处理手动输入逻辑 ---
manual_map = {}
if manual_input:
    pairs = [p.strip() for p in manual_input.split(",") if ":" in p]
    for p in pairs:
        try:
            s_code, s_date = p.split(":")
            # 尝试将字符串转换为日期对象
            manual_map[s_code.strip().upper()] = datetime.strptime(s_date.strip(), '%Y-%m-%d')
        except:
            st.sidebar.error(f"⚠️ 格式错误: {p} (请使用 YYYY-MM-DD)")

# --- 6. 主界面内容 ---
st.title("🛡️ 期货持仓 FND 风险监控")

if submit_button:
    symbols = [s.strip().upper() for s in raw_input.split(",") if s.strip()]
    
    for sym in symbols:
        try:
            with st.spinner(f'正在同步 {sym} 数据...'):
                ticker = yf.Ticker(sym)
                info = ticker.info
                specific_code = info.get('underlyingSymbol') or info.get('symbol') or sym
                
                # 抓取过期日
                expiry_date = None
                expiry_ts = info.get('lastTradingDay') or info.get('expireDate')
                if expiry_ts:
                    expiry_date = datetime.fromtimestamp(expiry_ts)
                if not expiry_date:
                    try:
                        cal = ticker.calendar
                        if not cal.empty: expiry_date = cal.iloc[0, 0]
                    except: pass

                if expiry_date:
                    if not isinstance(expiry_date, datetime):
                        expiry_date = datetime.combine(expiry_date, datetime.min.time())
                    
                    contract_info = get_contract_info(sym)
                    
                    # --- 精准判定：是否存在手动修正 ---
                    if sym in manual_map:
                        fnd_date = manual_map[sym]
                        fnd_label = "🦉 手动指定 FND"
                    else:
                        fnd_date = calculate_auto_fnd(sym, expiry_date)
                        fnd_label = "🤖 自动预估 FND"

                    days_to_fnd = (fnd_date - datetime.now()).days

                    # --- UI 展示卡片 ---
                    with st.container():
                        st.divider()
                        c1, c2 = st.columns([3, 2])
                        with c1:
                            st.subheader(f"{contract_info['name']} ({sym})")
                            st.info(f"📍 **合约月份代码: {specific_code}**")
                            st.write(f"结算方式：**{contract_info['type']}**")
                            st.write(f"最后交易日: `{expiry_date.strftime('%Y-%m-%d')}`")
                            st.write(f"{fnd_label}: `{fnd_date.strftime('%Y-%m-%d')}`")
                        
                        with c2:
                            if days_to_fnd <= 3:
                                st.error(f"🚨 距离移仓: {days_to_fnd} 天")
                            elif days_to_fnd <= 7:
                                st.warning(f"⏳ 距离移仓: {days_to_fnd} 天")
                            else:
                                st.success(f"✅ 距离移仓: {days_to_fnd} 天")
                else:
                    st.error(f"❌ 无法抓取 {sym} 数据。")
        except Exception as e:
            st.error(f"查询 {sym} 出错")
else:
    st.info("👈 请在左侧侧边栏输入持仓和修正信息。")