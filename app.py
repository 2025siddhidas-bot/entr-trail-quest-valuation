"""Trail Quest valuation model: simplified Streamlit app.

Run:  streamlit run app.py
Same maths as the Excel reference workbook (see model.py). Only the inputs teammates are likely to have are editable.
"""
import io, json
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import model as M
import proxy_data as PXD
from spec import SPEC, PARTS, STATUSES, SEAS_DEFAULT

st.set_page_config(page_title='Trail Quest valuation model', layout='wide')
COL = {'Bear': '#C0504D', 'Base': '#4F81BD', 'Bull': '#2E8B57'}
NY = 5                                     # years shown
YEARS = [f'Year {y}' for y in range(1, NY + 1)]

# ---------------------------------------------------------------- which inputs teammates see (plain wording)
# key: (plain label, unit shown)
SHOWN = {
    # Part 1
    'g_raise': ('Money we are raising', 'HK$'),
    'a_m0': ('Installs in the launch month, as % of the people we can reach', '%'),
    's1_d30': ('Planners: % of new users still active after 30 days', '%'),
    's2_d30': ('Players: % of new users still active after 30 days', '%'),
    's3_d30': ('Community-seekers: % of new users still active after 30 days', '%'),
    # Part 2
    'm_gamer': ('% of people who play mobile or video games', '%'),
    'm_int_a': ('...of those, % who would play a hiking game just for the game', '%'),
    'm_comm': ('% of people who want company for active or social outings', '%'),
    'm_int_b': ('...of those, % who would join through a game (play together, keep in touch)', '%'),
    'm_hiker': ('% of people who already hike', '%'),
    'm_intend': ('% of non-hikers who want to start hiking', '%'),
    'm_int_c': ('...of hikers and would-be hikers, % who would use it for trail info alone', '%'),
    's1_mix': ('Share of new installs who are planners', '%'),
    's2_mix': ('Share of new installs who are players', '%'),
    's3_mix': ('Share of new installs who are community-seekers', '%'),
    # Part 3
    'x_a_ratio': ('Taiwan: how many times bigger than Hong Kong', 'x'),
    'x_b_ratio': ('Japan, Korea, Singapore and Greater Bay Area: how many times bigger than Hong Kong', 'x'),
    # Part 4
    'r_cpc': ('Price an advertiser pays per click', 'HK$'),
    'r_ctr': ('% of ad views that get clicked', '%'),
    'r_arppu': ('Spend per paying user per month', 'HK$'),
    's1_p': ('Planners: % of active users who pay in a month', '%'),
    's2_p': ('Players: % of active users who pay in a month', '%'),
    's3_p': ('Community-seekers: % of active users who pay in a month', '%'),
    'r_instn': ('Paid partnerships per year (e.g. tourism bodies, brands)', 'number'),
    'r_instf': ('Fee per partnership per year', 'HK$'),
    'r_grant': ('Grants we expect to receive (not repaid)', 'HK$'),
    # Part 5
    'c_pre': ('Development cost before launch', 'HK$'),
    'c_team': ('Team cost per month', 'HK$'),
    'c_cpi': ('Cost to get one paid install', 'HK$'),
    'c_events': ('Community events budget per month', 'HK$'),
    'c_ga': ('Admin, legal and accounting per month', 'HK$'),
}

# ---------------------------------------------------------------- state
if 'inputs' not in st.session_state:
    st.session_state.inputs = M.default_inputs()
    st.session_state.meta = M.default_meta()
    st.session_state.seas = list(SEAS_DEFAULT)
    st.session_state.ver = 0
inputs, meta = st.session_state.inputs, st.session_state.meta


def disp(r, v): return round(v * 100, 4) if r['fmt'] == 'pct' else v
def stor(r, v): return round(v / 100, 6) if r['fmt'] == 'pct' else v
def usdm(x, fx=7.8):
    u = x / fx / 1e6
    return f'US${u:,.1f}M' if u >= 1 else f'US${u:,.2f}M'


def money(x, d=0): return '-' if x is None or (isinstance(x, float) and np.isnan(x)) else f'{x:,.{d}f}'


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.title('Trail Quest')
    detail = st.selectbox('Scenario to look at in detail', M.SCN, index=1, help='Bear = smaller success, Base = solid success, Bull = Pokemon Go-scale success')
    sidx = M.SCN.index(detail)
    st.caption('Bear = smaller success, Base = solid success, Bull = Pokemon Go-scale success.')
    st.divider()
    st.subheader('Save / load')
    st.download_button('Download all inputs', json.dumps({'inputs': inputs, 'meta': meta, 'seas': st.session_state.seas}, indent=1), 'trailquest_inputs.json', 'application/json', use_container_width=True)
    up = st.file_uploader('Load a saved inputs file', type='json', key=f'upj{st.session_state.ver}')
    if up is not None and st.button('Replace everything with this file', use_container_width=True):
        d = json.load(up)
        st.session_state.inputs = {k: d['inputs'].get(k, v) for k, v in M.default_inputs().items()}
        st.session_state.meta = {k: d['meta'].get(k, v) for k, v in M.default_meta().items()}
        st.session_state.seas = d.get('seas', list(SEAS_DEFAULT)); st.session_state.ver += 1; st.rerun()
    if st.button('Reset to defaults', use_container_width=True):
        st.session_state.inputs = M.default_inputs(); st.session_state.meta = M.default_meta()
        st.session_state.seas = list(SEAS_DEFAULT); st.session_state.ver += 1; st.rerun()

tabs = st.tabs(['Dashboard', 'Inputs', 'Market', 'Adoption', 'Revenue', 'Costs & profit', 'Evidence', 'Export'])

# ================================================================ INPUTS
with tabs[1]:
    st.header('Inputs')
    st.markdown('**Bear / Base / Bull** are three versions of success: smaller, solid and Pokemon Go-scale. '
                '**Status** says how solid the number is: SOURCED (from a published source), PROXY-BASED (taken from a similar game), PLACEHOLDER (our guess, please replace), DECISION (our choice).')
    ptabs = st.tabs([PARTS[p] for p in range(1, 6)] + ['Merge teammate files', 'Built-in assumptions'])
    for pi, p in enumerate(range(1, 6)):
        with ptabs[pi]:
            rows = [r for r in M.ROWS if r['part'] == p and r['key'] in SHOWN]
            scen = [r for r in rows if not r['glob']]; glob = [r for r in rows if r['glob']]
            if scen:
                df = pd.DataFrame({'Parameter': [SHOWN[r['key']][0] for r in scen], 'Unit': [SHOWN[r['key']][1] for r in scen],
                                   'Bear': [disp(r, inputs[r['key']][0]) for r in scen], 'Base': [disp(r, inputs[r['key']][1]) for r in scen], 'Bull': [disp(r, inputs[r['key']][2]) for r in scen],
                                   'Status': [meta[r['key']]['status'] for r in scen], 'Source': [r['source'] for r in scen]})
                ed = st.data_editor(df, hide_index=True, use_container_width=True, key=f'sc{p}_{st.session_state.ver}', disabled=['Parameter', 'Unit', 'Source'],
                                    column_config={'Parameter': st.column_config.TextColumn(width='large'), 'Unit': st.column_config.TextColumn(width='small'),
                                                   'Bear': st.column_config.NumberColumn(format='%g'), 'Base': st.column_config.NumberColumn(format='%g'), 'Bull': st.column_config.NumberColumn(format='%g'),
                                                   'Status': st.column_config.SelectboxColumn(options=STATUSES, required=True), 'Source': st.column_config.TextColumn(width='large')})
                for i, r in enumerate(scen):
                    k = r['key']
                    inputs[k] = [stor(r, float(ed.loc[i, c])) if pd.notna(ed.loc[i, c]) else inputs[k][j] for j, c in enumerate(['Bear', 'Base', 'Bull'])]
                    meta[k] = {'status': ed.loc[i, 'Status'], 'owner': meta[k].get('owner', '')}
            if glob:
                gdf = pd.DataFrame({'Parameter': [SHOWN[r['key']][0] for r in glob], 'Unit': [SHOWN[r['key']][1] for r in glob], 'Value': [disp(r, inputs[r['key']][1]) for r in glob],
                                    'Status': [meta[r['key']]['status'] for r in glob], 'Source': [r['source'] for r in glob]})
                ge = st.data_editor(gdf, hide_index=True, use_container_width=True, key=f'gl{p}_{st.session_state.ver}', disabled=['Parameter', 'Unit', 'Source'],
                                    column_config={'Parameter': st.column_config.TextColumn(width='large'), 'Value': st.column_config.NumberColumn(format='%g'),
                                                   'Status': st.column_config.SelectboxColumn(options=STATUSES, required=True), 'Source': st.column_config.TextColumn(width='large')})
                for i, r in enumerate(glob):
                    k = r['key']
                    if pd.notna(ge.loc[i, 'Value']): inputs[k] = [stor(r, float(ge.loc[i, 'Value']))] * 3
                    meta[k] = {'status': ge.loc[i, 'Status'], 'owner': meta[k].get('owner', '')}
            if p == 2:
                mix = [sum(inputs[f's{i}_mix'][s] for i in (1, 2, 3)) for s in range(3)]
                if any(abs(x - 1) > 1e-4 for x in mix): st.error('The three install shares must add to 100% in each column (now: ' + ', '.join(f'{x:.0%}' for x in mix) + ').')
            exp = pd.DataFrame([{'key': r['key'], 'parameter': SHOWN[r['key']][0], 'bear': disp(r, inputs[r['key']][0]), 'base': disp(r, inputs[r['key']][1]), 'bull': disp(r, inputs[r['key']][2]), 'status': meta[r['key']]['status']} for r in rows])
            st.download_button(f'Download Part {p} as CSV', exp.to_csv(index=False), f'trailquest_part{p}.csv', 'text/csv', key=f'dl{p}')
    with ptabs[5]:
        st.markdown('Each teammate fills only their own Part (download its CSV, fill it in, upload it here). Rows are matched by `key`; nothing else changes.')
        ups = st.file_uploader('Part CSV files', type='csv', accept_multiple_files=True, key=f'upc{st.session_state.ver}')
        if ups and st.button('Merge these files'):
            n = 0; unk = []
            for f in ups:
                d = pd.read_csv(f)
                for _, row in d.iterrows():
                    k = row['key']
                    if k not in SHOWN: unk.append(k); continue
                    r = M.BYKEY[k]; vals = [stor(r, float(row[c])) for c in ('bear', 'base', 'bull')]
                    inputs[k] = [vals[1]] * 3 if r['glob'] else vals
                    if 'status' in row and row['status'] in STATUSES: meta[k] = {'status': row['status'], 'owner': meta[k].get('owner', '')}
                    n += 1
            st.session_state.ver += 1; st.success(f'Merged {n} rows.' + (f' Skipped unknown keys: {sorted(set(unk))}' if unk else '')); st.rerun()
    with ptabs[6]:
        st.markdown('These are fixed in the model so the team does not have to fill them in. They come from the real games we use as comparisons (Pokemon Go, Pikmin Bloom, Monster Hunter Now) or from standard industry figures. Read-only.')
        hid = [r for r in M.ROWS if r['key'] not in SHOWN and r['key'] not in ('g_exit', 'p_w') and not r['key'].startswith('sc_') and not r['key'].startswith('v5_')]
        hd = pd.DataFrame({'Assumption': [r['label'] for r in hid], 'Unit': [r['unit'] for r in hid], 'Bear': [disp(r, inputs[r['key']][0]) for r in hid], 'Base': [disp(r, inputs[r['key']][1]) for r in hid], 'Bull': [disp(r, inputs[r['key']][2]) for r in hid], 'Source': [r['source'] for r in hid]})
        st.dataframe(hd, hide_index=True, use_container_width=True)
        st.caption('Also fixed: the three cases are weighted 25% / 50% / 25%, the valuation looks 5 years ahead, and seasonality is switched off.')

# ================================================================ RUN
out = M.run_all(inputs, st.session_state.seas, meta)
S = out['scn']
fails = [c['check'] for c in out['checks'] if c['type'] == 'FAIL' and 'FAIL' in (c['Bear'], c['Base'], c['Bull'])]


def fig(title, h=340):
    f = go.Figure(); f.update_layout(title=title, height=h, margin=dict(t=50, b=10), legend=dict(orientation='h', y=-0.2)); return f


# ================================================================ DASHBOARD
with tabs[0]:
    st.header('What is Trail Quest worth?')
    if fails: st.error('Something in the inputs does not add up: ' + '; '.join(fails))
    with st.container(border=True):
        st.markdown('**Valuation method: the VC method** (based on how venture investors usually value a young company)')
        st.markdown('Based on answering *what could this company be sold for in 5 years, and what is it worth today so that I earn the return I expect?* '
                    'So we (1) forecast our revenue in year 5, (2) multiply it by what similar companies sell for as a multiple of yearly revenue, '
                    '(3) take off the share that future investors will own, and (4) scale the result back to today at the return investors expect (60% a year). '
                    'The 60% already covers the risk that the company fails, so each case below describes the company **succeeding**, not failing.')
        st.markdown('**What the forecast is anchored to:** Pokemon Go at its peak (232M monthly users in 2016, about 8.9% of the world\'s mobile gamers, and roughly US$1B of revenue that year). '
                    'Bull = Trail Quest reaches the 8.9% share of gamers in Hong Kong and the other Asian markets. Base and Bear reach a smaller share.')
    st.caption('Bear = smaller success, Base = solid success, Bull = Pokemon Go-scale success. Numbers use placeholder inputs until the team fills in the Inputs tab.')
    c = st.columns(3)
    for i, n in enumerate(M.SCN):
        v = S[i]['val']
        with c[i]:
            with st.container(border=True):
                st.markdown(f'**{n}**')
                st.metric('Company value today (US$)', usdm(v['post1'], inputs['g_fx'][1]))
                st.caption(f"HK${money(v['post1'])}  \nRevenue in year 5: {usdm(v['rev5'], inputs['g_fx'][1])}  \nActive users in year 5: {money(v['mau5'])}  \nBest month in Hong Kong: {S[i]['monthly'].mau_hk.max() / (S[i]['market']['eligpop'] * S[i]['market']['phone'] * S[i]['market']['reachA']):.1%} of gamers (Pokemon Go peak: 8.9%)")
    g1, g2 = st.columns(2)
    f = fig('Revenue by year (HK$)')
    for i, n in enumerate(M.SCN): f.add_bar(x=YEARS, y=S[i]['annual'].revenue[1:NY + 1], name=n, marker_color=COL[n])
    g1.plotly_chart(f, use_container_width=True)
    f = fig('Average active users by year')
    for i, n in enumerate(M.SCN): f.add_scatter(x=YEARS, y=S[i]['annual'].mau_total[1:NY + 1], name=n, line=dict(color=COL[n]))
    g2.plotly_chart(f, use_container_width=True)
    with st.expander('How the company value is calculated, step by step'):
        rows_ = [('1. Revenue in year 5 (HK$)', 'rev5', 'n'), ('2. Sale multiple (what similar companies sell for, as a multiple of yearly revenue)', 'mult', 'x'),
                 ('3. Value of the company if sold in year 5 (1 x 2)', 'ev1', 'n')]
        t = pd.DataFrame({'Step': [r[0] for r in rows_] + ['4. Share owned by future investors (reduces what today\'s investors keep)', '5. Value kept by today\'s investors in year 5 (3 less 4)', '6. Growth factor needed to give investors their 60% a year over 5 years', '7. Company value today (5 divided by 6)', '   In US$']})
        for i, n in enumerate(M.SCN):
            v = S[i]['val']
            t[n] = [money(v['rev5']), f"{v['mult']:.1f}x", money(v['ev1']), f"{v['dil']:.0%}", money(v['ev1'] * (1 - v['dil'])), f"{(1 + v['irr']) ** v['exit_year']:.1f}x", money(v['post1']), usdm(v['post1'], inputs['g_fx'][1])]
        st.dataframe(t, hide_index=True, use_container_width=True)
    ph = [meta[r['key']]['status'] for r in M.ROWS if r['key'] in SHOWN]
    share = ph.count('PLACEHOLDER') / len(ph)
    st.progress(1 - share, text=f'{ph.count("PLACEHOLDER")} of {len(ph)} inputs are still placeholders ({1 - share:.0%} have a source or come from a similar game)')

# ================================================================ MARKET
with tabs[2]:
    st.header('How many people could use the app?')
    st.markdown('You do not need to hike to use Trail Quest. Three groups could use it: **players** (people who like the game), **community-seekers** (people who want company for outings) and **planners** (hikers who want trail info).')
    c1, c2 = st.columns(2)
    f = fig('From everyone who could use it to people we can reach (people)')
    for i, n in enumerate(M.SCN): f.add_bar(x=['Everyone who could use it', 'People who would actually use it', 'Installs we can reach in 5 years'], y=[S[i]['market'][k] for k in ('tam', 'sam', 'som')], name=n, marker_color=COL[n])
    c1.plotly_chart(f, use_container_width=True)
    f = fig('Who would actually use it, by group (people)')
    for nm, k, cc in (('Players', 'poolA', '#7030A0'), ('Community-seekers', 'poolB', '#ED7D31'), ('Planners', 'poolC', '#70AD47')): f.add_bar(x=M.SCN, y=[S[i]['market'][k] for i in range(3)], name=nm, marker_color=cc)
    f.update_layout(barmode='stack'); c2.plotly_chart(f, use_container_width=True)
    m = S[sidx]['market']
    st.markdown(f"**{detail} case in words:** of {m['pop']:,.0f} people in Hong Kong, about **{m['tam']:,.0f}** could use the app (TAM). About **{m['sam']:,.0f}** would actually use it (SAM). "
                f"We aim to reach about **{m['som']:,.0f}** of them as installs over 5 years (SOM), starting with about **{m['m0']:,.0f}** in the launch month.")
    with st.expander('Detailed numbers'):
        labels = [('pop', 'Hong Kong population', 'int'), ('eligpop', 'Aged 12 and over', 'int'), ('phone', 'Smartphone users (share)', 'pct'), ('reachA', 'Play games', 'pct'), ('reachB', 'Want company for outings', 'pct'), ('reachC', 'Hike or want to hike', 'pct'),
                  ('tam', 'Everyone who could use it (TAM)', 'int'), ('poolA', 'Would use it: players', 'int'), ('poolB', 'Would use it: community-seekers', 'int'), ('poolC', 'Would use it: planners', 'int'), ('poolsum', 'People counted in more than one group', 'int'),
                  ('sam', 'People who would actually use it (SAM)', 'int'), ('som', 'Installs we can reach in 5 years (SOM)', 'int'), ('m0', 'Installs in the launch month', 'int')]
        mt = pd.DataFrame({'': [l for _, l, _ in labels], **{n: [(f"{S[i]['market'][k]:.1%}" if f_ == 'pct' else f"{S[i]['market'][k]:,.0f}") for k, _, f_ in labels] for i, n in enumerate(M.SCN)}})
        st.dataframe(mt, hide_index=True, use_container_width=True)

# ================================================================ ADOPTION
with tabs[3]:
    st.header('How many people will use the app over time?')
    ks = list(range(0, 25)); f = fig('Our launch curve vs real games (new installs as % of the first month)', h=400)
    for i, n in enumerate(M.SCN):
        p_ = S[i]['p']; f.add_scatter(x=ks, y=[p_['a_floor'] + (1 - p_['a_floor']) * 0.5 ** (k / p_['a_half']) for k in ks], name=f'{n}', line=dict(color=COL[n]))
    f.add_scatter(x=ks, y=PXD.POGO_ACTUAL[:25], mode='markers', name='Pokemon Go (real)', marker=dict(color=COL['Bull'], symbol='x'))
    f.add_scatter(x=list(range(len(PXD.MHN_ACTUAL))), y=PXD.MHN_ACTUAL, mode='markers', name='Monster Hunter Now (real)', marker=dict(color=COL['Bear'], symbol='x'))
    f.update_xaxes(title='Months after launch'); f.update_yaxes(tickformat='.0%', range=[0, 0.6]); st.plotly_chart(f, use_container_width=True)
    st.caption('Real location-based games all follow the same pattern: a big spike at launch, then most players drift away within a couple of months, leaving a steady core. We use the same shape.')
    d = S[sidx]['monthly']; c1, c2 = st.columns(2)
    f = fig('New installs per month'); _ = [f.add_scatter(x=S[i]['monthly'].month, y=S[i]['monthly'].new_installs, name=n, line=dict(color=COL[n])) for i, n in enumerate(M.SCN)]
    f.update_xaxes(title='Month since launch'); c1.plotly_chart(f, use_container_width=True)
    f = fig(f'{detail}: active users by type'); _ = [f.add_scatter(x=d.month, y=d[col], name=nm, stackgroup='one', line=dict(color=cc)) for nm, col, cc in (('Planners', 'mau_planners', '#70AD47'), ('Players', 'mau_players', '#7030A0'), ('Community-seekers', 'mau_community', '#ED7D31'))]
    c2.plotly_chart(f, use_container_width=True)
    st.subheader('Average active users per year')
    u = pd.DataFrame({n: S[i]['annual'].mau_total.values[1:NY + 1] for i, n in enumerate(M.SCN)}, index=YEARS)
    st.dataframe(u.style.format('{:,.0f}'), use_container_width=True)
    st.caption('Hong Kong plus the later launches in other markets (Taiwan, Japan/Korea/Singapore/Greater Bay Area).')

# ================================================================ REVENUE
with tabs[4]:
    st.header('Where does the money come from?')
    st.markdown('**Ads:** brands pay each time a user clicks their ad on a trail. **In-app purchases:** some users pay for extras in the game. **Partnerships:** tourism bodies or brands pay a yearly fee. **Other markets:** the same app launched later in Taiwan and elsewhere.')
    A = S[sidx]['annual']
    c1, c2 = st.columns(2)
    f = fig(f'{detail}: revenue by source (HK$)')
    for nm, col in (('Ads', 'ad_hk'), ('In-app purchases', 'iap_hk'), ('Partnerships', 'institutional'), ('Other markets: Taiwan', 'exp_a'), ('Other markets: Japan, Korea, Singapore, GBA', 'exp_b')): f.add_bar(x=YEARS, y=A[col].values[1:NY + 1], name=nm)
    f.update_layout(barmode='stack'); c1.plotly_chart(f, use_container_width=True)
    f = fig('Total revenue per month (HK$)'); _ = [f.add_scatter(x=S[i]['monthly'].month, y=S[i]['monthly'].revenue, name=n, line=dict(color=COL[n])) for i, n in enumerate(M.SCN)]
    c2.plotly_chart(f, use_container_width=True)
    st.subheader('Revenue per year (HK$)')
    st.dataframe(pd.DataFrame({n: S[i]['annual'].revenue.values[1:NY + 1] for i, n in enumerate(M.SCN)}, index=YEARS).style.format('{:,.0f}'), use_container_width=True)
    st.subheader(f'{detail}: how much each user brings in')
    ue = pd.DataFrame({'Year': YEARS, 'Revenue (HK$)': A.revenue.values[1:NY + 1], 'Revenue per active user (HK$)': A.rev_per_user.values[1:NY + 1], 'Share of revenue from ads': A.ad_share.values[1:NY + 1]})
    st.dataframe(ue.style.format({'Revenue (HK$)': '{:,.0f}', 'Revenue per active user (HK$)': '{:,.1f}', 'Share of revenue from ads': '{:.0%}'}), hide_index=True, use_container_width=True)
    st.caption('For comparison, Pikmin Bloom earned about HK$10.9 per download in its first year.')

# ================================================================ COSTS & PROFIT
with tabs[5]:
    st.header('Costs and profit')
    A = S[sidx]['annual']
    c1, c2 = st.columns(2)
    f = fig(f'{detail}: revenue vs costs (HK$)'); f.add_bar(x=YEARS, y=A.revenue.values[1:NY + 1], name='Revenue', marker_color='#2E8B57'); f.add_bar(x=YEARS, y=A.costs.values[1:NY + 1], name='Costs', marker_color='#C0504D')
    c1.plotly_chart(f, use_container_width=True)
    f = fig('Cash balance by month (HK$): how much money we need'); _ = [f.add_scatter(x=S[i]['monthly'].month, y=S[i]['monthly'].cum_cash, name=n, line=dict(color=COL[n])) for i, n in enumerate(M.SCN)]
    f.add_hline(y=-inputs['g_raise'][1], line_dash='dash', annotation_text='Money we are raising'); c2.plotly_chart(f, use_container_width=True)
    st.caption('The dashed line is the money we plan to raise. A line that drops below it means we would run out of cash before that point.')
    st.subheader(f'{detail}: summary by year (HK$)')
    s_ = pd.DataFrame({'Revenue': A.revenue.values[1:NY + 1], 'Costs': A.costs.values[1:NY + 1], 'Profit or loss': A.ebit.values[1:NY + 1], 'Cash position at year end': A.cum_cash_flow.values[1:NY + 1]}, index=YEARS).T
    st.dataframe(s_.style.format('{:,.0f}'), use_container_width=True)
    with st.expander('All cost lines'):
        names = {'c_pre': 'Development before launch', 'c_team': 'Team', 'c_cloud': 'Cloud and hosting', 'c_ua': 'Paid user acquisition', 'c_events': 'Community events', 'c_sales': 'Sales commission', 'c_data': 'Data and licences', 'c_ga': 'Admin, legal and accounting', 'c_expansion': 'Other-market costs', 'costs': 'Total costs', 'tax': 'Profits tax', 'grant': 'Grants received'}
        pl = A[list(names)].T.iloc[:, :NY + 1]; pl.index = list(names.values()); pl.columns = ['Before launch'] + YEARS
        st.dataframe(pl.style.format('{:,.0f}'), use_container_width=True)

# ================================================================ EVIDENCE
with tabs[6]:
    st.header('Evidence: the real games and data behind the defaults')
    fit = PXD.FITTED
    st.subheader('Real games we compare against')
    sn = pd.DataFrame([{'Game': n, 'Monthly revenue (US$)': r, 'Downloads in Oct 2026': d, 'Hong Kong share of downloads': s} for n, r, d, s in PXD.SNAPSHOT])
    st.dataframe(sn.style.format({'Monthly revenue (US$)': '{:,.0f}', 'Downloads in Oct 2026': '{:,.0f}', 'Hong Kong share of downloads': '{:.1%}'}, na_rep='n/a'), hide_index=True, use_container_width=True)
    st.caption('Source: AppMagic, Oct 2026, revenue after app-store fees. One month only, so treat as a rough run-rate.')
    st.subheader('How fast real games lose users')
    st.dataframe(pd.DataFrame(PXD.RETENTION, columns=['Benchmark', 'Day 1', 'Day 7', 'Day 30', 'Source']).style.format({'Day 1': '{:.1%}', 'Day 7': '{:.1%}', 'Day 30': '{:.1%}'}, na_rep='-'), hide_index=True, use_container_width=True)
    st.subheader('Sale multiples of similar companies')
    cp = pd.DataFrame([{'Company': n, 'Value (US$)': ev, 'Yearly revenue (US$)': rv, 'Value as a multiple of revenue': ev / rv, 'Source': src} for n, ev, rv, mau, src in PXD.COMPS])
    st.dataframe(cp.style.format({'Value (US$)': '{:,.0f}', 'Yearly revenue (US$)': '{:,.0f}', 'Value as a multiple of revenue': '{:.1f}x'}), hide_index=True, use_container_width=True)
    st.subheader('Return investors expect (per year)')
    st.dataframe(pd.DataFrame(PXD.INVESTOR_RETURNS, columns=['Stage', 'Low', 'High', 'Source']).style.format({'Low': '{:.0%}', 'High': '{:.0%}'}), hide_index=True, use_container_width=True)

# ================================================================ EXPORT
with tabs[7]:
    st.header('Export')
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as xw:
        pd.DataFrame({n: {'Company value today (HK$)': S[i]['val']['post1'], 'Company value today (US$)': S[i]['val']['post1'] / inputs['g_fx'][1], 'Revenue in year 5 (HK$)': S[i]['val']['rev5'], 'Active users in year 5': S[i]['val']['mau5']} for i, n in enumerate(M.SCN)}).to_excel(xw, sheet_name='Summary')
        pd.DataFrame([{'key': r['key'], 'parameter': r['label'], 'unit': r['unit'], 'bear': disp(r, inputs[r['key']][0]), 'base': disp(r, inputs[r['key']][1]), 'bull': disp(r, inputs[r['key']][2]), 'status': meta[r['key']]['status'], 'source': r['source']} for r in M.ROWS]).to_excel(xw, sheet_name='Inputs', index=False)
        for i, n in enumerate(M.SCN):
            S[i]['annual'].T.to_excel(xw, sheet_name=f'Annual_{n}'); S[i]['monthly'].to_excel(xw, sheet_name=f'Monthly_{n}', index=False)
    st.download_button('Download results (Excel)', buf.getvalue(), 'trailquest_results.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
