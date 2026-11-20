# Trail Quest valuation model (simplified app)

    pip install -r requirements.txt
    streamlit run app.py

Pages: Dashboard (the one valuation number per case + how it is calculated), Inputs (only what teammates are likely to have, by Part), Market, Adoption, Revenue, Costs & profit, Evidence, Export.
Everything not on the Inputs tab is a built-in assumption (see Inputs > Built-in assumptions, read-only).
Teammates can fill their Part as a CSV and merge it (Inputs > Merge teammate files).
`TrailQuest_Valuation_Model.xlsx` is the full reference with every method and check; it gives the same numbers.
Script / Colab: `python run_cli.py --inputs trailquest_inputs.json --out results.xlsx`
