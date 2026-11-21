"""Trail Quest valuation model: Python engine.

Mirrors the Excel workbook (TrailQuest_Valuation_Model.xlsx) formula by formula:
Inputs -> Market -> monthly model (60 months) -> Annual -> Valuation -> Checks.
No Streamlit code here, so it can also be run from a script or a Colab notebook.
"""
import math
import numpy as np
import pandas as pd
from spec import SPEC, SEAS_DEFAULT, NIANTIC_EV_USD, NIANTIC_MAU
import proxy_data as PXD

SCN = ['Bear', 'Base', 'Bull']
T = 84          # 7 years: lets the exit year be 3 to 7
MAXY = T // 12
ROWS = [r for r in SPEC if 'key' in r]
KEYS = [r['key'] for r in ROWS]
BYKEY = {r['key']: r for r in ROWS}


def default_inputs():
    """{key: [bear, base, bull]} from the spec."""
    return {r['key']: list(r['vals']) for r in ROWS}


def default_meta():
    """{key: {'status':..., 'owner':''}}"""
    return {r['key']: {'status': r['status'], 'owner': ''} for r in ROWS}


def scen_params(inputs, s):
    p = {k: v[s] for k, v in inputs.items()}
    # global rows hold one value for every scenario
    for r in ROWS:
        if r['glob']:
            p[r['key']] = inputs[r['key']][1]
    return p


# ---------------------------------------------------------------- market
def market(p):
    m = {}
    m['pop'] = p['g_pop']; m['elig'] = p['m_elig']; m['eligpop'] = m['pop'] * m['elig']
    m['phone'] = p['m_phone']
    m['reachA'] = p['m_gamer']
    m['hiker'] = p['m_hiker']; m['intend'] = p['m_intend']
    m['reachC'] = m['hiker'] + (1 - m['hiker']) * m['intend']
    m['tam'] = m['eligpop'] * m['phone'] * (1 - (1 - m['reachA']) * (1 - m['reachC']))
    m['intA'] = p['m_int_a']; m['intC'] = p['m_int_c']
    m['poolA'] = m['eligpop'] * m['phone'] * m['reachA'] * m['intA']
    m['poolC'] = m['eligpop'] * m['phone'] * m['reachC'] * m['intC']
    m['sam'] = m['eligpop'] * m['phone'] * (1 - (1 - m['reachA'] * m['intA']) * (1 - m['reachC'] * m['intC']))
    m['poolsum'] = m['poolA'] + m['poolC'] - m['sam']
    m['uni'] = p['m_uni']; m['unishare'] = m['uni'] / m['sam'] if m['sam'] else 0
    m['maxpen'] = p['m_maxpen']; m['som'] = m['sam'] * m['maxpen']
    m['m0pct'] = p['a_m0']; m['m0'] = m['sam'] * m['m0pct']
    m['pikhk'] = PXD.PIKMIN_HK_MONTHLY_DOWNLOADS
    m['ratio'] = m['m0'] / m['pikhk']
    return m


# ---------------------------------------------------------------- monthly engine
def monthly(p, seas_idx, mk):
    avg = sum(seas_idx) / 12
    ceiling = mk['som']; m0 = mk['m0']
    rpi = {1: p['r_cpm'] / 1000, 2: p['r_ctr'] * p['r_cpc'], 3: p['r_ctr'] * p['r_vconv'] * p['r_cpv']}[int(p['r_model'])]
    scA = p['x_a_ratio'] * p['x_a_eff']; scB = p['x_b_ratio'] * p['x_b_eff']
    rows = []
    cum = 0.0; ret = [0.0, 0.0, 0.0]
    for t in range(1, T + 1):
        yr = math.ceil(t / 12); moy = (int(p['a_launch']) - 1 + t - 1) % 12 + 1
        seas = 1 + p['a_seas'] * (seas_idx[moy - 1] / avg - 1)
        camp = 1 if moy == int(p['a_campm']) else 0
        shape = p['a_floor'] + (1 - p['a_floor']) * 0.5 ** ((t - 1) / p['a_half'])
        raw = m0 * shape * seas * (1 + camp * p['a_campu'])
        room = max(0, ceiling - cum)
        new = min(raw * max(0, 1 - cum / ceiling), room) if ceiling > 0 else 0
        cum += new
        nseg = [new * p[f's{i+1}_mix'] for i in range(3)]
        mau = []; newret = []
        for i in range(3):
            base = ret[i] * (1 - p[f's{i+1}_ch'])
            mau.append(base + nseg[i]); newret.append(base + nseg[i] * p[f's{i+1}_d30'])
        ret = newret; MAU = sum(mau)
        views = sum(mau[i] * p[f's{i+1}_v'] for i in range(3)) * seas
        impr = views * p['r_place']
        fill = min(p['r_fillt'], p['r_fills'] + (p['r_fillt'] - p['r_fills']) * (t - 1) / max(1, p['r_fillr']))
        sold = impr * fill; ad = sold * rpi
        payers = sum(mau[i] * p[f's{i+1}_p'] for i in range(3))
        iapg = payers * p['r_arppu']; iapn = iapg * (1 - p['r_fee'])
        inst = p['r_instn'] * p['r_instf'] / 12 if yr >= p['r_insty'] else 0
        rows.append(dict(month=t, year=yr, cal_month=moy, seasonality=seas, campaign=camp, curve=shape, installs_raw=raw, room=room,
                         new_installs=new, cum_installs=cum, new_planners=nseg[0], new_players=nseg[1], new_community=nseg[2],
                         mau_planners=mau[0], mau_players=mau[1], mau_community=mau[2], mau_hk=MAU,
                         trail_views=views, impressions=impr, fill_rate=fill, sold_impressions=sold, ad_rev=ad,
                         payers=payers, iap_gross=iapg, iap_net=iapn, institutional=inst))
    df = pd.DataFrame(rows)
    df['hk_rev'] = df.ad_rev + df.iap_net + df.institutional
    for X, sc, pre in (('a', scA, 'x_a'), ('b', scB, 'x_b')):
        d = int(p[pre + '_delay']); mau = []; ad = []; iap = []; cost = []
        for t in range(1, T + 1):
            if sc > 0 and t > d:
                src = df.iloc[t - d - 1]
                mx = sc * src.mau_hk; ax = sc * p[pre + '_rev'] * src.ad_rev; ix = sc * p[pre + '_rev'] * src.iap_net
            else:
                mx = ax = ix = 0.0
            cx = (p[pre + '_cost'] * (ax + ix) + (p[pre + '_launch'] if t == d + 1 else 0)) if sc > 0 else 0.0
            mau.append(mx); ad.append(ax); iap.append(ix); cost.append(cx)
        df[f'x{X}_mau'] = mau; df[f'x{X}_ad'] = ad; df[f'x{X}_iap'] = iap; df[f'x{X}_rev'] = np.array(ad) + np.array(iap); df[f'x{X}_cost'] = cost
    df['exp_mau'] = df.xa_mau + df.xb_mau; df['mau_total'] = df.mau_hk + df.exp_mau
    df['revenue'] = df.hk_rev + df.xa_rev + df.xb_rev
    df['c_team'] = p['c_team'] * (1 + p['c_teamg']) ** (df.year - 1)
    df['c_cloud'] = p['c_cloudf'] + p['c_cloudm'] * df.mau_total
    df['c_ua'] = df.new_installs * (1 - p['c_org']) * p['c_cpi']
    df['c_events'] = p['c_events']
    df['c_sales'] = p['c_sales'] * (df.ad_rev + df.institutional)
    df['c_data'] = p['c_data']; df['c_ga'] = p['c_ga']
    df['c_expansion'] = df.xa_cost + df.xb_cost
    df['costs'] = df[['c_team', 'c_cloud', 'c_ua', 'c_events', 'c_sales', 'c_data', 'c_ga', 'c_expansion']].sum(axis=1)
    df['ebit'] = df.revenue - df.costs
    df['cum_cash'] = -p['c_pre'] + p['r_grant'] + df.ebit.cumsum()
    df['rev_per_1000_impr'] = rpi * 1000
    return df, rpi


# ---------------------------------------------------------------- annual
def annual(df, p):
    A = pd.DataFrame(index=range(0, MAXY + 1))
    g = df.groupby('year')
    def s(col): return pd.Series({y: g[col].sum().get(y, 0.0) for y in range(1, MAXY + 1)}).reindex(range(0, MAXY + 1)).fillna(0.0)
    def a(col): return pd.Series({y: g[col].mean().get(y, 0.0) for y in range(1, MAXY + 1)}).reindex(range(0, MAXY + 1)).fillna(0.0)
    A['new_installs'] = s('new_installs'); A['mau_hk'] = a('mau_hk'); A['mau_exp'] = a('exp_mau'); A['mau_total'] = a('mau_total')
    A['mau_dec'] = [0] + [df.mau_total.iloc[12 * y - 1] for y in range(1, MAXY + 1)]
    A['ad_hk'] = s('ad_rev'); A['iap_hk'] = s('iap_net'); A['institutional'] = s('institutional'); A['exp_a'] = s('xa_rev'); A['exp_b'] = s('xb_rev')
    A['revenue'] = A.ad_hk + A.iap_hk + A.institutional + A.exp_a + A.exp_b
    A['growth'] = [np.nan, np.nan] + [A.revenue[y] / A.revenue[y - 1] - 1 if A.revenue[y - 1] > 0 else np.nan for y in range(2, MAXY + 1)]
    A['ad_all'] = A.ad_hk + s('xa_ad') + s('xb_ad'); A['iap_all'] = A.iap_hk + s('xa_iap') + s('xb_iap')
    A['ad_share'] = np.where(A.revenue > 0, A.ad_all / A.revenue.replace(0, np.nan), 0)
    A['advertisers_needed'] = A.ad_all / 12 / p['r_advs']
    A['c_pre'] = [p['c_pre']] + [0] * MAXY
    for k in ('team', 'cloud', 'ua', 'events', 'sales', 'data', 'ga', 'expansion'): A['c_' + k] = s('c_' + k)
    A['costs'] = A[[c for c in A.columns if c.startswith('c_')]].sum(axis=1)
    A['ebit'] = A.revenue - A.costs
    A['ebit_margin'] = np.where(A.revenue > 0, A.ebit / A.revenue.replace(0, np.nan), np.nan)
    nolo = [0.0]; taxable = [0.0]; tax = [0.0]; nolc = [max(0, 0 - A.ebit[0])]
    for y in range(1, MAXY + 1):
        o = nolc[-1]; nolo.append(o); tx = max(0, A.ebit[y] - o); taxable.append(tx); tax.append(p['g_tax'] * tx); nolc.append(max(0, o - A.ebit[y]))
    A['tax_loss_open'] = nolo; A['taxable'] = taxable; A['tax'] = tax; A['tax_loss_close'] = nolc
    A['grant'] = [p['r_grant']] + [0] * MAXY
    A['net_cash_flow'] = A.ebit - A.tax + A.grant
    A['cum_cash_flow'] = A.net_cash_flow.cumsum()
    A['rev_per_user'] = np.where(A.mau_total > 0, A.revenue / A.mau_total.replace(0, np.nan), 0)
    A['core_rev_per_install'] = np.where(A.new_installs > 0, (A.ad_hk + A.iap_hk) / A.new_installs.replace(0, np.nan), 0)
    return A


# ---------------------------------------------------------------- valuation
def valuation(p, A, df, mk):
    v = {}
    n = int(round(p['g_exit'])); n = min(MAXY, max(3, n)); v['exit_year'] = n
    v['mult'] = p['v_mult']; v['irr'] = p['g_irr']; v['dil'] = p['g_dil']; v['disc'] = p['g_disc']; v['raise'] = p['g_raise']
    v['rev5'] = A.revenue[n]; v['ebit5'] = A.ebit[n]; v['mau5'] = A.mau_total[n]      # "5" in the key names = exit year (5 by default)
    cc = df.cum_cash.iloc[:12 * n]
    v['peak'] = -min(0, min(-p['c_pre'] + p['r_grant'], cc.min()))
    v['gap'] = max(0, v['peak'] - v['raise'])
    f = (1 - v['dil']) / (1 + v['irr']) ** n
    v['ev1'] = v['rev5'] * v['mult']; v['post1'] = v['ev1'] * f; v['pre1'] = v['post1'] - v['raise']
    v['stake1'] = v['raise'] / v['post1'] if v['post1'] > 0 else np.nan
    v['flag1'] = 'No value at these inputs' if v['post1'] <= 0 else ('Raise exceeds value' if v['raise'] > v['post1'] else 'Supported')
    v['vmau'] = NIANTIC_EV_USD / NIANTIC_MAU * p['g_fx'] * p['v_disc_mau']
    v['ev2'] = v['mau5'] * v['vmau']; v['post2'] = v['ev2'] * f; v['pre2'] = v['post2'] - v['raise']
    v['prox'] = p['v_prox'] * 1e6 * p['g_fx']; v['share'] = p['v_share']; v['rev3'] = v['prox'] * v['share']
    v['ev3'] = v['rev3'] * v['mult']; v['post3'] = v['ev3'] * f; v['pre3'] = v['post3'] - v['raise']
    v['gap3'] = v['rev5'] / v['rev3'] if v['rev3'] > 0 else 0
    v['npv'] = sum(A.net_cash_flow[y] / (1 + v['disc']) ** y for y in range(0, n + 1))
    v['tv'] = v['rev5'] * v['mult'] / (1 + v['disc']) ** n; v['npvt'] = v['npv'] + v['tv']
    v['target'] = p['g_target']; v['reqev'] = v['target'] * (1 + v['irr']) ** n / (1 - v['dil']); v['reqrev'] = v['reqev'] / v['mult']
    v['xrev'] = v['reqrev'] / v['rev5'] if v['rev5'] > 0 else np.nan
    v['reqmau'] = v['reqrev'] / (v['rev5'] / v['mau5']) if v['rev5'] > 0 else np.nan
    v['xpik'] = v['reqrev'] / (5e6 * 12 * p['g_fx'])
    v['usd1'] = v['post1'] / p['g_fx']; v['usd3'] = v['post3'] / p['g_fx']
    # Method 5: seed-round comparables x Payne scorecard (market-based, not DCF)
    v['bench5'] = p['v5_bench'] * 1e6                                   # US$
    v['score5'] = sum(p[f'sc_w{i}'] * p[f'sc_{i}'] for i in range(1, 8))
    v['pre5usd'] = v['bench5'] * v['score5']; v['pre5'] = v['pre5usd'] * p['g_fx']
    v['post5'] = v['pre5'] + v['raise']; v['post5usd'] = v['post5'] / p['g_fx']
    v['stake5'] = v['raise'] / v['post5'] if v['post5'] > 0 else np.nan
    v['post5_vs_post1'] = v['post5'] / v['post1'] if v['post1'] > 0 else np.nan
    prof = df.index[(df.ebit > 0) & (df.month <= 12 * n)]
    v['first_profit_month'] = int(df.month[prof[0]]) if len(prof) else None
    return v


WEIGHTED_KEYS = ['pre5', 'post5', 'pre5usd', 'post5usd', 'rev5', 'ebit5', 'mau5', 'peak', 'gap', 'ev1', 'post1', 'pre1', 'ev2', 'post2', 'pre2', 'rev3', 'ev3', 'post3', 'pre3', 'npv', 'tv', 'npvt', 'usd1', 'usd3']


def run_one(inputs, seas, s):
    """Run a single scenario (used by the tornado, much faster than run_all)."""
    p = scen_params(inputs, s); mk = market(p)
    df, rpi = monthly(p, list(seas), mk); A = annual(df, p)
    return dict(p=p, market=mk, monthly=df, annual=A, val=valuation(p, A, df, mk), rpi=rpi)


def run_all(inputs, seas=None, meta=None):
    seas = list(seas) if seas is not None else list(SEAS_DEFAULT)
    out = {'scn': [], 'seas': seas}
    for s in range(3):
        p = scen_params(inputs, s)
        mk = market(p)
        df, rpi = monthly(p, seas, mk)
        A = annual(df, p)
        v = valuation(p, A, df, mk)
        out['scn'].append(dict(p=p, market=mk, monthly=df, annual=A, val=v, rpi=rpi))
    w = [out['scn'][s]['p']['p_w'] for s in range(3)]
    out['weights'] = w
    out['weighted'] = {k: sum(w[s] * out['scn'][s]['val'][k] for s in range(3)) for k in WEIGHTED_KEYS}
    out['checks'] = checks(out, inputs, meta)
    return out


def checks(out, inputs, meta=None):
    """Same tests as the Excel Checks sheet. Returns list of dicts."""
    C = []
    sc = out['scn']
    def add(name, vals, typ, note): C.append(dict(check=name, Bear=vals[0], Base=vals[1], Bull=vals[2], type=typ, note=note))
    add('Segment mix sums to 100%', ['PASS' if abs(sum(inputs[f's{i}_mix'][s] for i in (1, 2, 3)) - 1) < 1e-4 else 'FAIL' for s in range(3)], 'FAIL', 'Planner + player + community shares of new installs')
    wok = 'PASS' if abs(sum(inputs['p_w']) - 1) < 1e-4 else 'FAIL'
    add('Scenario weights sum to 100%', [wok] * 3, 'FAIL', 'Probability weights')
    add('Scorecard weights sum to 100%', ['PASS' if abs(sum(inputs[f'sc_w{i}'][1] for i in range(1, 8)) - 1) < 1e-4 else 'FAIL'] * 3, 'FAIL', 'Method 5 weights')
    add('Exit year is a whole number from 3 to 7', ['PASS' if 3 <= inputs['g_exit'][1] <= 7 and abs(inputs['g_exit'][1] - round(inputs['g_exit'][1])) < 1e-9 else 'FAIL'] * 3, 'FAIL', 'Model runs 7 years')
    add('Installs never exceed the ceiling', ['PASS' if sc[s]['monthly'].cum_installs.iloc[-1] / sc[s]['market']['som'] <= 1.0001 else 'FAIL' for s in range(3)] if all(sc[s]['market']['som'] > 0 for s in range(3)) else ['PASS'] * 3, 'FAIL', 'Cumulative installs / SOM ceiling')
    add('Revenue total equals sum of monthly revenue', ['PASS' if abs(sc[s]['annual'].revenue.sum() - sc[s]['monthly'].revenue.sum()) < 1 else 'FAIL' for s in range(3)], 'FAIL', 'Annual vs monthly')
    ordok = 'PASS' if sc[0]['val']['rev5'] <= sc[1]['val']['rev5'] <= sc[2]['val']['rev5'] else 'WARN'
    add('Scenario order: Bear <= Base <= Bull (exit-year revenue)', [ordok] * 3, 'WARN', 'Scenarios should rank in order')
    add('Raise covers peak funding need', ['PASS' if sc[s]['val']['gap'] <= 0 else 'WARN' for s in range(3)], 'WARN', 'If WARN, needs a later round or bigger raise')
    add('Launch-month installs vs Pikmin Bloom HK monthly downloads (x)', [sc[s]['market']['ratio'] for s in range(3)], 'INFO', 'Above about 5x is bold for a first month')
    pik = PXD.PIKMIN['year1_revenue_usd'] / PXD.PIKMIN['year1_downloads']
    add('Year-1 core revenue per install vs Pikmin Bloom (share)', [sc[s]['annual'].core_rev_per_install[1] / (pik * sc[s]['p']['g_fx']) for s in range(3)], 'INFO', 'Pikmin Bloom earned about US$1.40 per download in year 1')
    add('Exit-year Hong Kong installs per month (average)', [sc[s]['annual'].new_installs[sc[s]['val']['exit_year']] / 12 for s in range(3)], 'INFO', 'Pikmin Bloom HK about 7,200 and Monster Hunter Now about 1,350 a month')
    add('Exit-year ad share of revenue', [sc[s]['annual'].ad_share[sc[s]['val']['exit_year']] for s in range(3)], 'INFO', 'If low, ads are a minor stream unless price or fill rises')
    add('Advertisers needed in exit year (average)', [sc[s]['annual'].advertisers_needed[sc[s]['val']['exit_year']] for s in range(3)], 'INFO', 'How many retailers must buy')
    if meta is not None:
        share = sum(1 for k in KEYS if meta[k]['status'] == 'ASSUMPTION') / len(KEYS)
        add('Share of inputs still placeholders', [share] * 3, 'INFO', 'Readiness of the model')
    return C


def pricing_per_1000(p):
    return {'CPM': p['r_cpm'], 'CPC': 1000 * p['r_ctr'] * p['r_cpc'], 'Per store visit': 1000 * p['r_ctr'] * p['r_vconv'] * p['r_cpv']}


def tornado(inputs, seas, s, metric, swing=0.25):
    """Re-run the model with each numeric input moved by -/+swing; returns DataFrame."""
    base = run_one(inputs, seas, s)['val'][metric]
    res = []
    skip = {'g_fx', 'r_model', 'a_launch', 'a_campm', 'r_insty', 'p_w', 'g_pop', 'g_exit'}
    for r in ROWS:
        k = r['key']
        if k in skip or k.endswith('_mix') or k.startswith('sc_w'): continue
        vals = []
        for mult in (1 - swing, 1 + swing):
            inp = {kk: list(vv) for kk, vv in inputs.items()}
            if r['glob']: inp[k] = [inp[k][1] * mult] * 3
            else: inp[k][s] = inp[k][s] * mult
            vals.append(run_one(inp, seas, s)['val'][metric])
        res.append(dict(key=k, label=r['label'], low=vals[0], high=vals[1], base=base, swing=abs(vals[1] - vals[0])))
    return pd.DataFrame(res).sort_values('swing', ascending=False)
