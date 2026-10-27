import requests
from scipy.stats import skellam, poisson, nbinom
import re
import math

def get_kalshi_anchors(match, date):
    base_url = 'https://external-api.kalshi.com/trade-api/v2/markets?'
    event_tickers = ['KXWCGAME',
                    'KXWCTOTAL',
                    'KXWCBTTS',
                    'KXWC1HBTTS',
                    'KXWC2HBTTS',
                    'KXWCTEAMTOTAL',
                    'KXWC1H',
                    'KXWC2H']

    teams = []

    for ticker in event_tickers:
        url = f'{base_url}event_ticker={ticker}-{date}{match}'
        response = requests.get(url)
        data = response.json()
        for market in data.get('markets', []):
            if ticker == 'KXWCGAME':
                subtitle = market.get('yes_sub_title', '')
                if subtitle != "Reg Time: Tie":
                    teams.append(subtitle)
    team_a_unclean = teams[0]
    team_b_unclean = teams[1]
    team_a = team_a_unclean.replace('Reg Time: ', '')
    team_b = team_b_unclean.replace('Reg Time: ', '')
                    
    anchors = {f'Reg Time: {team_a}': 0.0,
            f'Reg Time: {team_b}': 0.0,
            'Reg Time: Tie': 0.0,
            'Reg Time: Over 0.5 goals scored': 0.0,
            'Reg Time: Over 2.5 goals scored': 0.0,
            'Reg Time: Both Teams To Score': 0.0,
            '1st Half: Both Teams To Score': 0.0,      
            '2nd Half: Both Teams To Score': 0.0,      
            f'Reg Time: {team_a} over 0.5 goals': 0.0,
            f'Reg Time: {team_b} over 0.5 goals': 0.0,  
            f'{team_a} wins 1st Half': 0.0,            
            f'{team_b} wins 1st Half': 0.0,
            'Tie 1st Half': 0.0,
}

    for ticker in event_tickers:
        url = f'{base_url}event_ticker={ticker}-{date}{match}'
        response = requests.get(url)
        data = response.json()
        for market in data.get('markets', []):
            subtitle = market.get('yes_sub_title', '')
            if subtitle in anchors:
                prob = (float(market.get('yes_bid_dollars', '0')) + float(market.get('yes_ask_dollars', '0')))/2
                anchors[subtitle] = round(prob, 3)
    return anchors, team_a, team_b
    
match_anchors, team_a, team_b = get_kalshi_anchors(match = 'ESPARG', date = '26JUL19') # year + month + day

if match_anchors[f'Reg Time: {team_a}'] > match_anchors[f'Reg Time: {team_b}']:
    favorite = team_a
    underdog = team_b
    fav_prob = match_anchors[f'Reg Time: {team_a}']
elif match_anchors[f'Reg Time: {team_b}'] > match_anchors[f'Reg Time: {team_a}']:
    favorite = team_b
    underdog = team_a
    fav_prob = match_anchors[f'Reg Time: {team_b}']

match_questions = [
    "Will the first goal of the match be credited with an assist in regulation (90 minutes + stoppage time)? Settles No if the match is 0-0.",
    "Will either team score 2 or more goals in the same half of regulation (90 minutes + stoppage time)?",
    "Will both teams score in regulation (90 minutes + stoppage time)?",
    "Will a goal be scored before the first hydration break?",
    "Will Spain have 5 or more shots on target in regulation (90 minutes + stoppage time)?",
    "Will a goal be scored after the second hydration break in regulation (90 minutes + stoppage time)?",
    "Will there be 5 or more total cards in regulation (90 minutes + stoppage time)?",
    "Will Argentina have 4 or more shots on target in regulation (90 minutes + stoppage time)?",
    "Will a penalty kick be scored in regulation (90 minutes + stoppage time)?",
    "Will the match be tied at the end of regulation (90 minutes + stoppage time) and go to extra time?",
    "Will a substitute score or assist a goal (excluding own goals) in regulation (90 minutes + stoppage time)?",
    "Will there be 5 or more offsides (both teams combined) in regulation (90 minutes + stoppage time)?",
    "Will Lamine Yamal (Spain, #19) record more shots on target than Lionel Messi (Argentina, #10) in regulation (90 minutes + stoppage time)?",
    "Will Spain have more corner kicks than Argentina in regulation (90 minutes + stoppage time)?",
    "Will 5 or more different Spain players attempt a shot in regulation (90 minutes + stoppage time)?",
    "Will there be 10 or more total corner kicks (both teams combined) in regulation (90 minutes + stoppage time)?",
    "Will there be 22 or more total shots (on and off target) in regulation (90 minutes + stoppage time)?",
    "Will Lamine Yamal (Spain, #19) score or assist a goal (excluding own goals) in regulation (90 minutes + stoppage time)?",
    "Will Lionel Messi (Argentina, #10) score or assist a goal (excluding own goals) in regulation (90 minutes + stoppage time)?",
    "Will Argentina win the World Cup?"
]

def team_lambdas(anchors, favorite, underdog):
    favorite_score = anchors.get(f'Reg Time: {favorite} over 0.5 goals')
    underdog_score = anchors.get(f'Reg Time: {underdog} over 0.5 goals')
    lambda_favorite_goals = -math.log(max(1 - favorite_score, 0.01))
    lambda_underdog_goals = -math.log(max(1 - underdog_score, 0.01))
    return lambda_favorite_goals, lambda_underdog_goals

lambda_favorite_goals, lambda_underdog_goals = team_lambdas(match_anchors, favorite, underdog)

# Constants
first_half_goals = 0.45   # fraction of goals/shots in 1st half
second_half_goals = 0.55   # fraction of goals/shots in 2nd half

# lambdas (calculated from past WC2026 stats)

lambda_inputs = {
    'fav_goals': 1.35,            'und_goals': 1.05,   # market-derived — REPLACE raw weighted
    'fav_sot_rate': 5.043,        'und_sot_rate': 5.551,
    'fav_foul_rate': 11.951,      'und_foul_rate': 12.694,
    'fav_card_rate': 0.997,       'und_card_rate': 1.578,
    'fav_corner_rate': 5.005,     'und_corner_rate': 5.356,
    'fav_offside_rate': 2.92,     'und_offside_rate': 2.806,
    'fav_shot_rate': 14.612,      'und_shot_rate': 14.678,
    'messi_goals_per_match': 0.893,    'messi_sot_per_match': 1.843,
    'messi_assists_per_match': 0.878,
    'yamal_goals_per_match': 0.06,     'yamal_assists_per_match': 0.0,
    'yamal_sot_per_match': 1.218,
    'alvarez_goals_per_match': 0.172,  'alvarez_assists_per_match': 0.131,
    'ref_card_rate': 3.131,
}

# negative binomial functions

goal_dispersion_r = 6.0

def nb_pmf(k, lam, r):
    r = goal_dispersion_r 
    p = r / (r + lam)

    return nbinom.pmf(k, r, p)

def nb_cdf(k, lam, r):
    r = goal_dispersion_r 
    p = r / (r + lam)

    return nbinom.cdf(k, r, p)

def nb_sf(k, lam, r):
    r = goal_dispersion_r 
    p = r / (r + lam)

    return nbinom.sf(k, r, p)

# total __ functions

def total_goals(question, anchors, favorite, underdog):
    lambda_total_goals = lambda_favorite_goals + lambda_underdog_goals
    if "or fewer" in question:
        match = re.search(r'(\d+) or fewer', question.lower())
        goal_max = int(match.group(1))
        prob = nb_cdf(goal_max, lambda_total_goals, goal_dispersion_r)
    
    elif "exactly" in question:
        match = re.search(r'exactly (\d+) total goals', question.lower())
        exact_goals = int(match.group(1))
        prob = nb_pmf(exact_goals, lambda_total_goals, goal_dispersion_r)
    
    elif "or more" in question:
        match = re.search(r'(\d+) or more', question.lower())
        goals_min = int(match.group(1))
        prob = nb_sf(goals_min - 1, lambda_total_goals, goal_dispersion_r)

    return round(prob, 4)

def odd_goals(question, anchors, favorite, underdog):
    lambda_total_goals = lambda_favorite_goals + lambda_underdog_goals
    prob = sum(nb_pmf(k, lambda_total_goals, goal_dispersion_r) for k in range(1, 20, 2))

    return round(prob, 4)

def total_offsides(question, anchors, favorite, underdog):
    lambda_total_offsides = lambda_inputs['fav_offside_rate'] + lambda_inputs['und_offside_rate']
    match = re.search(r'(\d+) or more', question.lower())
    offside_threshold = int(match.group(1))
    prob = 1 - poisson.cdf(offside_threshold - 1, lambda_total_offsides)

    return round(prob, 4)

def total_shots(question, anchors, favorite, underdog):
    lambda_total_shots = lambda_inputs['fav_shot_rate'] + lambda_inputs['und_shot_rate']
    match = re.search(r'(\d+) or more', question.lower())
    shot_threshold = int(match.group(1))
    prob = 1 - poisson.cdf(shot_threshold - 1, lambda_total_shots)

    return round(prob, 4)

def total_cards(question, anchors, favorite, underdog):
    lambda_team_cards = lambda_inputs['fav_card_rate'] + lambda_inputs['und_card_rate']
    lambda_ref_cards = lambda_inputs['ref_card_rate']
    lambda_total_cards = lambda_ref_cards * 0.7 + 0.3 * lambda_team_cards
    match = re.search(r'(\d+) or more', question.lower())
    card_min = int(match.group(1))
    prob = 1 - poisson.cdf(card_min - 1, lambda_total_cards)

    return round(prob, 4)

def team_sot_total(question, anchors, favorite, underdog):
    if favorite in question:
        lambda_shots = lambda_inputs['fav_sot_rate']
    elif underdog in question:
        lambda_shots = lambda_inputs['und_sot_rate']
    
    match = re.search(r'(\d+) or more', question.lower())
    shot_threshold = int(match.group(1))
    if 'first half' in question.lower():
        lambda_shots *= first_half_goals
    elif 'second half' in question.lower():
        lambda_shots *= second_half_goals

    prob = 1 - poisson.cdf(shot_threshold - 1, lambda_shots)

    return round(prob, 4)

def team_advances(question, anchors, favorite, underdog):
    # P(team wins) + P(draw in regulation) * 0.50
    if underdog in question:
        underdog_win = anchors.get(f'Reg Time: {underdog}')
        draw = anchors.get(f'Reg Time: Tie')
        prob = underdog_win + draw * 0.50
    elif favorite in question:
        favorite_win = anchors.get(f'Reg Time: {favorite}')
        draw = anchors.get(f'Reg Time: Tie')
        prob = favorite_win + draw * 0.50
    return round(prob, 4)

def team_corners(question, anchors, favorite, underdog):
    match = re.search(r'(\d+) or more', question.lower())
    corner_threshold = int(match.group(1))

    if underdog in question:
        lambda_underdog_corners = lambda_inputs["und_corner_rate"]
        prob = 1 - poisson.cdf(corner_threshold - 1, lambda_underdog_corners)
    elif favorite in question:
        lambda_favorite_corners = lambda_inputs["fav_corner_rate"]
        prob = 1 - poisson.cdf(corner_threshold - 1, lambda_favorite_corners)

    return round(prob, 4)

# comparison functions

def yamal_more_sot_messi(question, anchors, favorite, underdog):
    lambda_yamal_sot = lambda_inputs['yamal_sot_per_match']
    lambda_messi_sot = lambda_inputs['messi_sot_per_match']
    prob = skellam.sf(0, lambda_yamal_sot, lambda_messi_sot)

    return round(prob, 4)

def team_more_corners(question, anchors, favorite, underdog):
    lamda_und = lambda_inputs['und_corner_rate']
    lambda_fav = lambda_inputs['fav_corner_rate']

    if favorite in question:
        prob_fav_more = skellam.sf(0, lambda_fav, lamda_und)
        return round(prob_fav_more, 4)

    elif underdog in question:
        prob_und_more = skellam.sf(0, lamda_und, lambda_fav)
        return round(prob_und_more, 4)

def skellam_more_cards(question, anchors, favorite, underdog):
    lambda_favorite = lambda_inputs['fav_card_rate']
    lambda_underdog = lambda_inputs['und_card_rate']

    if favorite in question:
        prob = skellam.sf(0, lambda_favorite, lambda_underdog)
    elif underdog in question:
        prob = skellam.sf(0, lambda_underdog, lambda_favorite)

    return round(prob, 4)

# before half/before break/stoppage time functions

def nil_nil_ht(question, anchors, favorite, underdog):
    lambda_total_goals = lambda_inputs['fav_goals'] + lambda_inputs['und_goals']
    lambda_first_half = lambda_total_goals * first_half_goals
    prob = nb_pmf(0, lambda_first_half, goal_dispersion_r)

    return round(prob, 4)

def offside_before_1stbreak(question, anchors, favorite, underdog):
    lambda_total = lambda_inputs['fav_offside_rate'] + lambda_inputs['und_offside_rate']
    lambda_1st_break = lambda_total * (22/90)
    prob = 1 - poisson.cdf(0, lambda_1st_break)

    return round(prob, 4)

def corners_before_first_break(question, anchors, favorite, underdog):
    lambda_total_corners = lambda_inputs['fav_corner_rate'] + lambda_inputs['und_corner_rate']
    break_fraction = 22/90
    lambda_corners_break = lambda_total_corners * break_fraction
    match = re.search(r'(\d+) or more', question.lower())
    corner_threshold = int(match.group(1))
    prob = 1 - poisson.cdf(corner_threshold - 1, lambda_corners_break)

    return round(prob, 4)

def goal_before_1st_break(question, anchors, favorite, underdog):
    lambda_total = lambda_inputs['fav_goals'] + lambda_inputs['und_goals']
    lambda_first_break = lambda_total * (22/90)
    prob = 1 - poisson.cdf(0, lambda_first_break)

    return round(prob, 4)

def goal_after_1st_break(question, anchors, favorite, underdog):
    lambda_favorite, lambda_underdog = team_lambdas(anchors, favorite, underdog)
    lambda_total = lambda_favorite + lambda_underdog
    lambda_first_break = lambda_total * (29/90)
    prob = 1 - poisson.cdf(0, lambda_first_break)

    return round(prob, 4)

def goal_after_2nd_break(question, anchors, favorite, underdog):
    lambda_total = lambda_inputs['fav_goals'] + lambda_inputs['und_goals']
    lambda_second_break = lambda_total * (29/90)
    prob = 1 - poisson.cdf(0, lambda_second_break)

    return round(prob, 4)

def goal_in_2nd_half_stoppage(question, anchors, favorite, underdog):
    lambda_total_goals = lambda_favorite_goals + lambda_underdog_goals
    stoppage_fraction = 6.0/96.0
    lambda_stoppage = lambda_total_goals * stoppage_fraction
    prob = 1 - poisson.cdf(0, lambda_stoppage)

    return round(prob, 4)

def card_first_half(question, anchors, favorite, underdog):
    lambda_total_cards = lambda_inputs['fav_card_rate'] + lambda_inputs['und_card_rate']
    first_half_fraction = 0.5
    lambda_first_half_cards = lambda_total_cards * first_half_fraction
    prob = 1 - poisson.cdf(0, lambda_first_half_cards)

    return round(prob, 4)

def team_scores_both_halves(question, anchors, favorite, underdog):
    if favorite in question:
        lam = lambda_favorite
    elif underdog in question:
        lam = lambda_underdog
    
    prob_score_1st = nb_sf(0, lam * 0.45, goal_dispersion_r)
    prob_score_2nd = nb_sf(0, lam * 0.55, goal_dispersion_r)
    
    prob = prob_score_1st * prob_score_2nd
    return round(prob, 4)

def card_during_stoppage(question, anchors, favorite, underdog):
    first_half_stoppage = 4.5
    second_half_stoppage = 6.0
    total_stoppage = first_half_stoppage + second_half_stoppage
    lambda_total_cards = 0.7 * lambda_inputs['ref_card_rate'] + 0.3 * (lambda_inputs['fav_card_rate'] + lambda_inputs['und_card_rate'])
    lambda_stoppage_cards = lambda_total_cards * total_stoppage / (total_stoppage + 90)
    prob = 1 - poisson.cdf(0, lambda_stoppage_cards)

    return round(prob, 4)
    
# player functions

def player_goal(question, anchors, favorite, underdog):
    if 'Messi' in question:
        lambda_goals = lambda_inputs['messi_goals_per_match']
        prob = nb_sf(0, lambda_goals, goal_dispersion_r)
    elif 'Yamal' in question:
        lambda_goals = lambda_inputs['yamal_goals_per_match']
        prob = nb_sf(0, lambda_goals, goal_dispersion_r)
    
    return round(prob, 4)

def player_assist(question, anchors, favorite, underdog):
    if 'Messi' in question:
        lambda_goals = lambda_inputs['messi_assists_per_match']
        prob = nb_sf(0, lambda_goals, goal_dispersion_r)
    elif 'Yamal' in question:
        lambda_goals = lambda_inputs['yamal_assists_per_match']
        prob = nb_sf(0, lambda_goals, goal_dispersion_r)
    
    return round(prob, 4)

def player_sots(question, anchors, favorite, underdog):
    if 'Breel' in question:
        match = re.search(r'(\d+) or more', question.lower())
        sots_threshold = int(match.group(1))
        lambda_sots = lambda_inputs['embolo_sot_per_match']
        prob = 1 - poisson.cdf(sots_threshold - 1, lambda_sots)
    elif 'Kane' in question:
        match = re.search(r'(\d+) or more', question.lower())
        sots_threshold = int(match.group(1))
        lambda_sots = lambda_inputs['kane_sot_per_match']
        prob = 1 - poisson.cdf(sots_threshold - 1, lambda_sots)
    
    return round(prob, 4)

def any_player_scores_2plus(question, anchors, favorite, underdog):
    player_lambdas = {
        'messi':      lambda_inputs['messi_goals_per_match'],
        'lautaro':    lambda_inputs.get('lautaro_goals_per_match', 0.15),  # floor, never scored in 3/4 games
        'mac_allister': 0.10,   # 0 goals across all games, small floor
        'enzo':       0.08,     # 0 goals across all games, small floor
        'alvarez':    lambda_inputs['alvarez_goals_per_match'] if lambda_inputs['alvarez_goals_per_match'] > 0 else 0.12,
        'salah':      lambda_inputs['salah_goals_per_match'],
        'marmoush':   0.10,     # 0 goals in 4 games, small floor
    }

    prob_none_2plus = 1.0
    for player, lam in player_lambdas.items():
        prob_none_2plus *= nb_cdf(1, lam) 

    prob = 1 - prob_none_2plus
    return round(prob, 4)

# Other

def spain_5plus_shooters(question, anchors, favorite, underdog):
    # Spain's total shot rate distributed across players
    # Historical: roughly 8-10 players attempt shots; we model each as independent
    # From data: top shooters and their approximate share of team shots
    total_shots = lambda_inputs['fav_shot_rate']  # 14.612

    # Approximate shot shares based on player data
    player_shot_shares = [0.18, 0.14, 0.13, 0.11, 0.10, 0.09, 0.08, 0.07, 0.06, 0.04]
    player_lambdas = [s * total_shots for s in player_shot_shares]

    # P(player attempts at least 1 shot)
    p_each_shoots = [1 - math.exp(-lam) for lam in player_lambdas]

    # P(exactly k players shoot) via dynamic programming
    n = len(player_lambdas)
    dp = [0.0] * (n + 1)
    dp[0] = 1.0
    for p in p_each_shoots:
        for j in range(n, 0, -1):
            dp[j] = dp[j] * (1 - p) + dp[j-1] * p
        dp[0] *= (1 - p)

    prob = sum(dp[k] for k in range(5, n+1))
    return round(prob, 4)

def either_team_2goals_same_half(question, anchors, favorite, underdog):
    lam_esp_1h = lambda_inputs['fav_goals'] * 0.45
    lam_esp_2h = lambda_inputs['fav_goals'] * 0.55
    lam_arg_1h = lambda_inputs['und_goals'] * 0.45
    lam_arg_2h = lambda_inputs['und_goals'] * 0.55

    # P(no team scores 2+ in 1st half) = P(ESP<=1 in 1H) * P(ARG<=1 in 1H)
    p_none_1h = nb_cdf(1, lam_esp_1h, goal_dispersion_r) * nb_cdf(1, lam_arg_1h, goal_dispersion_r)
    # P(no team scores 2+ in 2nd half)
    p_none_2h = nb_cdf(1, lam_esp_2h, goal_dispersion_r) * nb_cdf(1, lam_arg_2h, goal_dispersion_r)

    # P(neither half has a 2+ scorer) = both conditions hold simultaneously
    prob_none = p_none_1h * p_none_2h

    return round(1 - prob_none, 4)

def argentina_win_wc(question, anchors, favorite, underdog):
    prob_arg_win_reg = anchors['Reg Time: Argentina']
    prob_draw_reg = anchors['Reg Time: Tie'] 
    prob_arg_win_et = prob_draw_reg * 0.45
    prob_draw_et = prob_draw_reg * 0.25
    prob_arg_win_penalties = prob_draw_reg * prob_draw_et * 0.5

    prob = prob_arg_win_reg + prob_arg_win_et + prob_arg_win_penalties

    return round(prob, 4)

# prob = prob(goal) * prob(assist | goal scored)
def first_goal_has_assist(question, anchors, favorite, underdog):
    lambda_total_goals = lambda_inputs['fav_goals'] + lambda_inputs['und_goals']
    prob_goal = nb_sf(0, lambda_total_goals, goal_dispersion_r)
    prob_assist_given_goal = 0.75
    prob = prob_goal * prob_assist_given_goal

    return round(prob, 4)

def penalty_kick_scored(question, anchors, favorite, underdog):
    prob_penalty = 0.30
    prob_penalty_scored = 0.80
    prob = prob_penalty * prob_penalty_scored

    return round(prob, 4)

def second_half_more_goals(question, anchors, favorite, underdog):
    lambda_total_goals = lambda_favorite_goals + lambda_underdog_goals
    lambda_first_half = lambda_total_goals * first_half_goals
    lambda_second_half = lambda_total_goals * second_half_goals
    prob = 0.0
    for first_half in range(10):
        for second_half in range(10):
            if second_half > first_half:
                prob += nb_pmf(first_half, lambda_first_half, goal_dispersion_r) * nb_pmf(second_half, lambda_second_half, goal_dispersion_r)

    return round(prob, 4)

def england_more_corners_and_shots(question, anchors, favorite, underdog):
    lambda_england_corners = lambda_inputs['fav_corner_rate']
    lambda_norway_corners = lambda_inputs['und_corner_rate']
    lambda_england_shots = lambda_inputs['fav_shot_rate']
    lambda_norway_shots = lambda_inputs['und_shot_rate']

    prob = 0.0
    for england_corners in range(25):
        for norway_corners in range(25):
            for england_shots in range(40):
                for norway_shots in range(30):
                    if england_corners > norway_corners and england_shots > norway_shots:
                        prob += poisson.pmf(england_corners, lambda_england_corners) * poisson.pmf(norway_corners, lambda_norway_corners) * poisson.pmf(england_shots, lambda_england_shots) * poisson.pmf(norway_shots, lambda_norway_shots)

    return round(prob, 4)

def card_each_half(question, anchors, favorite, underdog):
    lambda_team = lambda_inputs['fav_card_rate'] + lambda_inputs['und_card_rate']
    lambda_ref = lambda_inputs['ref_card_rate']
    lambda_total = lambda_ref * 0.7 + lambda_team * 0.3
    p_card_1st_half = 1 - poisson.cdf(0, lambda_total * 0.5)
    p_card_2nd_half = 1 - poisson.cdf(0, lambda_total * 0.5)
    prob = p_card_1st_half * p_card_2nd_half

    return round(prob, 4)

def switzerland_holds_lead(question, anchors, favorite, underdog):
    prob_switzerland_never_leads = 0.0
    for arg in range(10):
        for sui in range(10):
            p_score = nb_pmf(arg, lambda_inputs['fav_goals'], goal_dispersion_r) * nb_pmf(sui, lambda_inputs['und_goals'], goal_dispersion_r)
            p_never = max(0, (arg - sui + 1)) / (arg + sui + 1)
            prob_switzerland_never_leads += p_score * p_never
    prob = 1 - prob_switzerland_never_leads

    return round(prob, 4)

def both_halves_same_goals(question, anchors, favorite, underdog):
    lambda_total = lambda_favorite_goals + lambda_underdog_goals
    lambda_first_half = lambda_total * first_half_goals
    lambda_second_half = lambda_total * second_half_goals
    prob = 0.0
    for i in range(10):
        prob += (nb_pmf(i, lambda_first_half, goal_dispersion_r) * nb_pmf(i, lambda_second_half, goal_dispersion_r))

    return round(prob, 4)

def penalty_or_red_card(question, anchors, favorite, underdog):
    prob_penalty = 0.12
    lambda_red = 0.7 * (1/3) + 0.3 * 0.35
    prob_red_card = 1 - math.exp(-lambda_red)
    prob = prob_penalty + prob_red_card - (prob_penalty * prob_red_card)

    return round(prob, 4)

def first_goal_not_messi_or_salah(question, anchors, favorite, underdog):
    lambda_total_goals = lambda_favorite_goals + lambda_underdog_goals
    prob_goal_is_scored = nb_sf(0, lambda_total_goals, goal_dispersion_r)
    prob_mos_score_given_goal = (lambda_total_goals - lambda_inputs['messi_goals_per_match'] - lambda_inputs['salah_goals_per_match']) / lambda_total_goals

    prob = prob_goal_is_scored * prob_mos_score_given_goal

    return round(prob, 4)

def btts_regulation(question, anchors, favorite, underdog):
    prob = anchors['Reg Time: Both Teams To Score']
    return round(prob, 4)

def halftime_tied(question, anchors, favorite, underdog):
    favorite_win_ht = anchors[f'{favorite} wins 1st Half']
    underdog_win_ht = anchors[f'{underdog} wins 1st Half']
    prob = round(max(0, 1 - favorite_win_ht - underdog_win_ht), 4)

    return prob

def team_scores_first(question, anchors, favorite, underdog):
    lambda_total = lambda_favorite_goals + lambda_underdog_goals
    if favorite in question:
        prob = (lambda_favorite / lambda_total) * (1 - poisson.cdf(0, lambda_total))
    elif underdog in question:
        prob = (lambda_underdog / lambda_total) * (1 - poisson.cdf(0, lambda_total))
    
    return round(prob, 4)

def penalty_shootout(question, anchors, favorite, underdog):
    prob_regulation_draw = anchors['Reg Time: Tie']
    prob_penalties_given_et = 0.55
    prob = prob_regulation_draw * prob_penalties_given_et
    
    return round(prob, 4)

def cards_vs_goals(question, anchors, favorite, underdog):
    lambda_team_cards = lambda_inputs['fav_card_rate'] + lambda_inputs['und_card_rate']
    lambda_ref_cards = lambda_inputs['ref_card_rate']
    lambda_total_cards = (lambda_team_cards + lambda_ref_cards) / 2
    lambda_total_goals = lambda_favorite_goals + lambda_underdog_goals

    prob = 0.0
    for i in range(15):
        for j in range(10):
            if i > j:
                prob += poisson.pmf(i, lambda_total_cards) * nb_pmf(j, lambda_total_goals, goal_dispersion_r)

    return round(prob, 4)

# Example Match Run

question_function_map = [
    (match_questions[0],  first_goal_has_assist),          # Q1  first goal has assist
    (match_questions[1],  either_team_2goals_same_half),   # Q2  either team 2+ goals same half
    (match_questions[2],  btts_regulation),                # Q3  BTTS
    (match_questions[3],  goal_before_1st_break),          # Q4  goal before 1st break
    (match_questions[4],  team_sot_total),                 # Q5  Spain 5+ SoT
    (match_questions[5],  goal_after_2nd_break),           # Q6  goal after 2nd break
    (match_questions[6],  total_cards),                    # Q7  5+ total cards
    (match_questions[7],  team_sot_total),                 # Q8  Argentina 4+ SoT
    (match_questions[8],  penalty_kick_scored),            # Q9  penalty kick scored
    (match_questions[9],  lambda q,a,f,u: round(a.get('Reg Time: Tie', 0.5), 4)),  # Q10 extra time
    (match_questions[10], lambda q,a,f,u: 0.22),           # Q11 sub scores/assists
    (match_questions[11], total_offsides),                 # Q12 5+ offsides
    (match_questions[12], yamal_more_sot_messi),           # Q13 Yamal more SoT than Messi
    (match_questions[13], team_more_corners),              # Q14 Spain more corners
    (match_questions[14], spain_5plus_shooters),           # Q15 5+ different Spain shooters
    (match_questions[15], lambda q,a,f,u: 0.39),           # Q16 10+ total corners
    (match_questions[16], total_shots),                    # Q17 22+ total shots
    (match_questions[17], lambda q,a,f,u: 0.43),           # Q18 Yamal G/A — Kalshi anchor
    (match_questions[18], lambda q,a,f,u: 0.59),           # Q19 Messi G/A
    (match_questions[19], argentina_win_wc),               # Q20 Argentina win WC
]

for i, (question, fn) in enumerate(question_function_map, 1):
    prob = fn(question, match_anchors, favorite, underdog)
    print(f"Q{i:<2} {prob:>6.1%}  {question}")
