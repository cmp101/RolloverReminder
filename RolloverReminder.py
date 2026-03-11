import streamlit as st
import yfinance as yf
from datetime import datetime, timedelta
import pandas as pd

# --- 1. 配置页面 ---
st.set_page_config(page_title="期货 FND 监控助手", page_icon="🛡️", layout="wide")

# --- 2. 品种结算属性词典 ---
def get_contract_info(symbol):
    specs = {
        "GC=F": {"name": "黄金", "type": "实物交割"},
        "SI=F": {"name": "白银", "type": "实物交割"},
        "HG=F": {"name": "铜", "type": "实物交割"},
        "CL=F": {"name": "原油(WTI)", "type": "实物交割"},
        "NG=F": {"name": "天然气", "type": "实物交割"},
        "RB=F": {"name": "汽油", "type": "实物交割"},
        "LE=F": {"name": "活牛", "type": "实物交割 (物理运输)"},
        "GF=F": {"name": "饲料牛", "type": "现金结算"},
        "HE=F": {"name": "瘦肉猪", "type": "现金结算"},
        "ES=F": {"name": "标普500", "type": "现金结算"},
        "NQ=F": {"name": "纳指100", "type": "现金结算"},
        "MES=F": {"name": "微型标普", "type": "现金结算"},
        "MNQ=F": {"name": "微型纳指", "type": "现金结算"},
    }
    return specs.get(symbol, {"name": "未知品种", "type": "请核实"})

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

# --- 4. 侧边栏与表单确认 ---
st.sidebar.header("⚙️ 持仓设置")
with st.sidebar.form("futures_input_form"):
    # 这里你可以修改 value 后面的内容，作为你的默认持仓
    raw_input = st.text_area("1. 监控品种 (逗号分隔)", value="MNQ=F, GF=F, LE=F")
    
    st.sidebar.write("---")
    #st.sidebar.subheader("2. 批量手动修正 (可选)")
    manual_input = st.text_area("格式: 代码:YYYY-MM-DD", value="LE=F:2026-04-06", placeholder="例如: GC=F:2026-03-25, LE=F:2026-04-06")
    
    submit_button = st.form_submit_button("确认并刷新数据")

# --- 5. 处理手动输入 ---
manual_map = {}
if manual_input:
    pairs = [p.strip() for p in manual_input.split(",") if ":" in p]
    for p in pairs:
        try:
            s_code, s_date = p.split(":")
            manual_map[s_code.strip().upper()] = datetime.strptime(s_date.strip(), '%Y-%m-%d')
        except:
            st.sidebar.error(f"格式错误: {p}")

# --- 6. 主界面内容 ---
st.title("Roller Reminder")

if submit_button or raw_input:
    symbols = [s.strip().upper() for s in raw_input.split(",") if s.strip()]
    
    for sym in symbols:
        try:
            with st.spinner(f'正在同步 {sym} 数据...'):
                ticker = yf.Ticker(sym)
                info = ticker.info
                specific_code = info.get('underlyingSymbol') or info.get('symbol') or sym
                
                # --- 年份纠偏逻辑 ---
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
                    
                    if sym in manual_map:
                        fnd_date = manual_map[sym]
                        fnd_label = "📍 手动指定 FND"
                    else:
                        fnd_date = calculate_auto_fnd(sym, expiry_date)
                        fnd_label = "🤖 自动预估 FND"

                    days_to_fnd = (fnd_date - datetime.now()).days

                    with st.container():
                        st.divider()
                        c1, c2 = st.columns([3, 2])
                        with c1:
                            st.subheader(f"{contract_info['name']} ({sym})")
                            st.info(f"📍 **具体合约代码: {specific_code}**")
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
            st.error(f"查询 {sym} 出错")




