"""Run the Trail Quest model without Streamlit (script / Colab / notebook).

    python run_cli.py                                  # defaults, prints a summary
    python run_cli.py --inputs trailquest_inputs.json  # inputs saved from the app
    python run_cli.py --inputs my.json --out results.xlsx

In a Colab or Jupyter notebook:
    import model as M
    out = M.run_all(M.default_inputs(), meta=M.default_meta())
    out['scn'][1]['annual']       # Base annual table (pandas)
    out['scn'][1]['val']          # Base valuation dict
"""
import argparse, json
import pandas as pd
import model as M
from spec import SEAS_DEFAULT


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--inputs', help='JSON saved from the app (Download all inputs)')
    ap.add_argument('--out', help='write results to this .xlsx')
    a = ap.parse_args()
    inputs, meta, seas = M.default_inputs(), M.default_meta(), list(SEAS_DEFAULT)
    if a.inputs:
        d = json.load(open(a.inputs))
        inputs = {k: d['inputs'].get(k, v) for k, v in inputs.items()}
        meta = {k: d['meta'].get(k, v) for k, v in meta.items()}
        seas = d.get('seas', seas)
    out = M.run_all(inputs, seas, meta)
    rows = ['rev5', 'ebit5', 'mau5', 'peak', 'post1', 'post2', 'post3', 'npv', 'npvt', 'reqrev']
    t = pd.DataFrame({n: {k: out['scn'][i]['val'][k] for k in rows} for i, n in enumerate(M.SCN)})
    t['Weighted'] = [out['weighted'].get(k, float('nan')) for k in rows]
    pd.set_option('display.float_format', '{:,.0f}'.format)
    print(t)
    print('\nChecks with FAIL:', [c['check'] for c in out['checks'] if 'FAIL' in (c['Bear'], c['Base'], c['Bull'])] or 'none')
    if a.out:
        with pd.ExcelWriter(a.out, engine='openpyxl') as xw:
            t.to_excel(xw, 'Summary')
            for i, n in enumerate(M.SCN):
                out['scn'][i]['annual'].T.to_excel(xw, f'Annual_{n}'); out['scn'][i]['monthly'].to_excel(xw, f'Monthly_{n}', index=False)
        print('wrote', a.out)


if __name__ == '__main__':
    main()
