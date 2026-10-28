# Jump-Trading-Probability-Cup
A probabilistic forecasting project developed for the 2026 Jump Trading FIFA World Cup Probability Cup. The competition involved submitting probabilities for 10-15 questions per match, such as "Will Messi have 1+ shots on target?" or "Will Norway have more corners than Senegal?" I finished in the top 6% of 4,000+ competitors, earning 1,920 Relative Brier Points across 551 forecasts.

## Scoring

Contestants were scored on a Relative Brier Points system. After submitting your match probabilities, your forecasts would be compared to the crowd average forecasts with this system. The two equations used were YBS = (py - pa)**2 and CBS = (pc - pa)**2, where YBS is your brier score for a specific question, py is the probability you submitted for that question, pa is the probability of the actual outcome (settles to 1 if the outcome of the question was YES and 0 if the outcome of the question was NO), CBS is the crowd's Brier Score, and pc is the probability the crowd submitted for that question (computed by averaging all contestant's probabilities for that question). Then, the points you received for that question, the Relative Brier Points (RBP) was calculated by computing RBP = YBS - CBS. 

## Data Sources

Kalshi: All forecasts began from Kalshi market prices. A set of anchors was pulled from Kalshi for every match to "anchor" each forecast with liquid market prices. The anchors included each team's win price, draw price, each team scoring 1+ goal, match having 1+ goal, and both teams scoring, among other anchors (full set of anchors in model file). These anchors were used as inputs to the probability distributions utilized to model each question. 

FBref: FBref was used for to reasons: to blend WC2026 team statistics with Kalshi prices and to model questions that didn't have Kalshi markets. Questions like "Will there be 4+ cards in the match?" did not have a corresponding Kalshi market price, so I utilized each team's FBref statistics from past matches in WC2026 to model such questions (for example, if Sweden has played 2 matches in the group stage and is currently playing their 3rd, I would use card data from their first 2 matches to model a cards question). 

NOTE: the above FBref method only worked because I joined the competition when most teams were playing their 2nd group stage match, so at the very least I had data from their first group stage match. My thought process was that the matches in WC2026 were the best indicators for predicting statistics in future WC2026 matches (rather than using matches before WC2026, such as in WC Qualifying, since those would be against different teams and would not mirror the same conditions as the actual WC). Intuitively, my predictions became more accurate as the competition progressed since I had more WC2026 matches to use data from. But if had I joined from the beginning, I would have defaulted to using Kalshi prices (as well as sportsbooks like DraftKings and FanDuel) for liquid markets and would have estimated probabilities of questions not on Kalshi using matches from before the WC (but as close to the WC as possible) as well as other inputs before I had actual WC2026 match data.

## Core Inputs

**Favorite/Underdog**
In addition to the Kalshi anchors detailed above, the model ran on additional inputs. Firstly, I derived the favorite and underdog of each match based on their win market prices (this was done for organization and debugging purposes rather than a modeling purpose; it was quite obvious in matches like Argentina vs. Algeria who was the favorite and who was the underdog, which ensured that I didn't have to keep scrolling back up to the top of my model to see who was team_a and who was team_b - just by seeing I needed Argentina for a specific question meant I needed to use favorite. Debugging weird outputs was also easier when I could easily identify which team was the favorite and which was the underdog). 

**lambda_inputs**
The lambda_inputs dictionary was a set of inputs derived from FBref match statistics (note that FBref didn't have referee card data, so I searched online for past international match card data of each referee). The name "lambda" was motivated by the fact that the mean of a Poisson distribution is lambda. The only caveat is that I also backed out expected goals for each team using their win market price, and used that early in the competition when I didn't have much FBref data. In the middle of the competition I defaulted to using FBref goal data to compute expected goals, but later realized that Kalshi prices most likely had priced that in, which is why I went back to using the win probability backed out expected goals. This might be a bit confusing and all over the place but it was my first time predicting soccer matches, so I wasn't perfect in my methodology.

**goal_dispersion_r**
As is detailed below, goals were modeled using the Negative Binomial distribution. I initially used Poisson, but realized that Poisson underestimated dispersion (variance) in goal data (goal counts vary match to match and expected goals itself is uncertain), so I transitioned to using Negative Binomial. The idea is that variance under Poisson = lambda, while variance under Negative Binomial = lambda + lambda**2/r, where r is the dispersion parameter. I started from a rough range of 5-8 which I got from AI-assisted research on overdispersion in goals, and I settled on 6 as a moderate value between the range. If I had to go back I'd use a better method to estimate the value of the parameter (such as using maximum likelihood on past WC2026 match scores). 

**Constants**
Two constants were used: first_half_goals = 0.45 and second_half_goals = 0.55. These are from empirical estimates (but on the more moderate end; many estimates said 40% in first half and 60% in second half, but since this was an estimate I wanted to be on a more moderate side).

## Bots

The competition allowed bots connected to LLMs to submit forecasts for you. I connected Claude to the platform, which pulled the list of questions for each match that I would copy paste into my model. The question_function_map at the bottom of the model was how my model matched the current match's questions to the corresponding functions (each question type was modeled by a function) in my model (after I modeled each question, Claude would create the question map. Since many question types were used across many matches, all I had to do was change inputs for each match, model the few questions that were new, and Claude would handle the function-to-question mapping).

## Modeling Approach

My model used 3 distributions to model each question type:

| Question type | Approach | Why I chose it |
|---|---|---|
| Goals | Negative Binomial | Allowed variance greater than the mean |
| Corners, cards, shots | Poisson | Baseline model for count events |
| Comparative outcomes | Skellam | Modeled differences between independent Poisson counts |

Each question type is represented by a function in the model that takes in the inputs above. 

EXAMPLE:
```python
def total_shots(question, anchors, favorite, underdog):
    lambda_total_shots = lambda_inputs['fav_shot_rate'] + lambda_inputs['und_shot_rate']
    match = re.search(r'(\d+) or more', question.lower())
    shot_threshold = int(match.group(1))
    prob = 1 - poisson.cdf(shot_threshold - 1, lambda_total_shots)

    return round(prob, 4)
```

The above example is for a total shots question (Will there be __ or more total shots?"). It computes an expected total shots using the favorite team's shot rate and underdog shot rate. It then takes in the question (the question_function_map at the bottom of the model maps the specific question in match_questions, so this function would only take in a total shots question). It would then get the specific string in the question that says "__ or more total shots" where __ has the shot threshold for the question. It then converts the number in the string to an integer and uses a Poisson distribution to derive the probability of __ or more shots. The rest of the functions work similarly.

After probabilities were computed for all questions, I routed the probabilities to Google Gemini to flag any inconsistencies (certain questions could be correlated with others - submitting a high probability for a team scoring 2+ goals but submitting a low probability for the same team having more than 4 shots on target is not consistent). I also manually checked lineups to see if certain players being mentioned in the questions were in the starting lineup or on the bench. Lineups were posted about an hour before the match, so after I had my probabilities, I would check if a certain player who I forecasted to have 2+ shots on target was on the bench - meaning he would likely be substituted on around the 60th-70th minute, giving him a much lower chance of having 2+ shots on target. I would then manually decrease the probability (if I forecasted that question to be 40%, for example, I would submit 15-20% instead, since my 40% was under the assumption that he was playing the entire match, but 15-20% is a stronger estimate if he is only playing 20-40 minutes). This became a strong source of edge, since many contestants would submit higher probabilities despite those players being on the bench, and often those questions would resolve to NO because the player either wouldn't come on or would come on for a very short period of time.

## Evaluation

I evaluated performance by tracking my Relative Brier Points compared to other contestants and reviewed competition platform reports that detailed my forecasts compared to what actually happened and calibration/performance in each question category. By the end of the competition, the model performed strongest in the Goals & Scoring category, beating the crowd on 251 out of 356 forecasts (crowd beat rate of 70%).

## Limitations

Some of these limitations may have been detailed above, but they are detailed here as well:

1. The FBref blending strategy used a small sample size of matches for each team, and many Kalshi markets had already priced most of these statistics in.
2. The overdispersion parameter wasn't fitted to historical data so it was a less reliable estimate.
3. Kalshi was only one market I used - I definitely should have used sportsbooks and other liquid estimates to get more reliable predictions.

## Setup

To run this properly, you would need to import the requests, re, and math libraries. And you would also need to import skellam, poisson, nbinom from scipy.stats. The base url for Kalshi works exactly how it is written in the model with no API key.

