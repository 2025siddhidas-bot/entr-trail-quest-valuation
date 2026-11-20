# Proxy reference data (copied from TrailQuest_Core_Proxy_Data.xlsx; see sources there)
POGO_ACTUAL = [1.0, 0.1423, 0.0771, 0.0623, 0.0835, 0.1188, 0.0882, 0.0525, 0.049, 0.0444, 0.0468, 0.0599, 0.0522, 0.0374, 0.0429, 0.0284, 0.0476, 0.0351, 0.0327, 0.035, 0.0377, 0.0316, 0.0472, 0.0581, 0.0433, 0.0502, 0.0409, 0.0384, 0.0631, 0.0369, 0.0425, 0.0328, 0.0331, 0.0448, 0.044, 0.0551, 0.0505, 0.0405, 0.0355, 0.0394, 0.0381, 0.0358, 0.0353, 0.0485, 0.0327, 0.0413, 0.0407, 0.0628, 0.0453, 0.0408, 0.0427, 0.0397, 0.0474, 0.0358, 0.0367, 0.0356, 0.0291, 0.0335, 0.0434, 0.0635, 0.0458, 0.0387, 0.0376, 0.0351, 0.0373, 0.0319, 0.0276, 0.0332, 0.0299, 0.0299, 0.0359, 0.0331, 0.0318, 0.0276, 0.0263, 0.0239, 0.0312, 0.0293, 0.0275, 0.029, 0.0235, 0.0267, 0.0344, 0.0306, 0.0361, 0.031, 0.0266, 0.0179, 0.022, 0.0195, 0.0248, 0.0312, 0.0258, 0.0245, 0.0248, 0.0285, 0.024, 0.0247, 0.0259, 0.0213, 0.0177, 0.0147, 0.0184, 0.0213, 0.0194, 0.0177, 0.0233, 0.0205, 0.0206, 0.0166, 0.0178, 0.0178, 0.0163, 0.0147, 0.0167, 0.0228, 0.0188, 0.0204, 0.0185, 0.0331, 0.0234, 0.0219]   # new installs as share of peak month, k = months after peak
MHN_ACTUAL = [1.0, 0.4544, 0.1083, 0.1614, 0.0573, 0.0446, 0.1083, 0.0446, 0.0446, 0.0786, 0.0913, 0.1231, 0.0446, 0.0318, 0.0361, 0.0297]
PIKMIN = dict(launch_month_downloads=3.2e6, oct2026_downloads=180000, year1_downloads=6.8e6, year1_revenue_usd=9.5e6)
SNAPSHOT = [  # AppMagic Oct 2026, monthly revenue after store fees (US$), downloads, HK share
    ('Monster Hunter Now (Bear)', 3e6, 45000, 0.03),
    ('Pikmin Bloom (Base)', 5e6, 180000, 0.04),
    ('Pokemon Go (Bull)', 38e6, 2000000, None)]
FITTED = dict(half=(0.7, 0.66, 0.3), floor=(0.06, 0.05625, 0.046))   # Bear/Base/Bull = MHN / Pikmin / PoGo
COMPS = [
    ('Scopely buys Niantic games (incl. Pokemon Go, Pikmin Bloom)', 3.5e9, 1.0e9, 30e6, 'Scopely announcement 12 Mar 2025; revenue ">$1B" so multiple is at most 3.5x'),
    ('Playtika (public)', 2.9e9, 2.8e9, None, 'multiples.vc, Oct 2026'),
    ('Roblox (public)', 34e9, 6.9e9, None, 'multiples.vc, Oct 2026')]
RETENTION = [  # name, D1, D7, D30, source
    ('Median mobile game, 2025', .22, .04, .007, 'GameAnalytics 2026 benchmarks'),
    ('Top 10% of games', .40, .12, .04, 'GameAnalytics 2026 benchmarks'),
    ('Top 1% of games', .66, None, .14, 'GameAnalytics via gameindustrylibrary.com'),
    ('"Good" game 2026 (vendor view)', .27, .11, .05, 'Segwise, Jul 2026')]
INVESTOR_RETURNS = [('Seed / idea stage', .50, .70, 'Equidam 2025; Damodaran via The VC Corner'), ('First stage / startup', .40, .60, 'Equidam'), ('Second stage / expansion', .30, .50, 'Equidam'), ('Start-up investors, general', .40, .70, 'Stanford E145')]
PIKMIN_HK_MONTHLY_DOWNLOADS = 180000*0.04
MHN_HK_MONTHLY_DOWNLOADS = 45000*0.03

SEED_COMPS = [  # name, US$M, used as, period, source
    ('Southeast Asia: median seed valuation', 2.0, 'Bear benchmark', '2025', 'DealStreetAsia / Kickstart Ventures via e27, 2 Sep 2026'),
    ('Europe: median pre-seed valuation', 3.48, 'Base benchmark', 'Q1 2026', 'Equidam Q1 2026 dataset'),
    ('Global: median pre-seed valuation', 5.87, 'Bull benchmark', 'Q1 2026', 'Equidam Q1 2026 dataset'),
    ('US: median pre-seed valuation', 7.64, 'Reference only (US-weighted)', 'Q1 2026', 'Equidam'),
    ('US: median consumer seed valuation', 13.6, 'Reference only', 'Q1 2025', 'Carta via causo.ai'),
    ('US: median seed pre-money', 18.4, 'Reference only', 'Q1 2026', 'PitchBook-NVCA via causo.ai'),
    ('US: median seed post-money, all sectors', 24.0, 'Reference only', 'Q4 2025', 'Carta'),
    ('US: median post-money SAFE cap, $1M-$2.5M rounds', 15.0, 'Reference only', '2025', 'Carta via waveup.com'),
    ('Southeast Asia: median seed round size (not a valuation)', 3.7, 'Reference only', 'H1 2026', 'DealStreetAsia / Kickstart via e27'),
    ('Southeast Asia: median pre-seed round size (not a valuation)', 0.9, 'Reference only', 'H1 2026', 'DealStreetAsia / Kickstart via e27')]
SEED_NOTE = 'Not used: Kratos Studios (India, web3 game) US$20M seed at a US$150M valuation, an outlier. US medians are not used because Hong Kong / Asia seed pricing is lower.'
