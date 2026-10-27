# Jump-Trading-Probability-Cup
A probabilistic forecasting project developed for the 2026 Jump Trading FIFA World Cup Probability Cup. The competition involved submitting probabilities for 10-15 questions per match, such as "Will Messi have 1+ shots on target?" or "Will Norway have more corners than Senegal?" I finished in the top 6% of 4,000+ competitors, earning 1,920 Relative Brier Points across 551 forecasts.

**Scoring**

Contestants were scored on a Relative Brier Points system. After submitting your match probabilities, your forecasts would be compared to the crowd average forecasts with this system. The two equations used were YBS = (py - pa)**2 and CBS = (pc - pa)**2, where YBS is your brier score for a specific question, py is the probability you submitted for that question, pa is the probability of the actual outcome (settles to 1 if the outcome of the question was YES and 0 if the outcome of the question was NO), CBS is the crowd's Brier Score, and pc is the probability the crowd submitted for that question (computed by averaging all contestant's probabilities for that question). Then, the points you received for that question, the Relative Brier Points (RBP) was calculated by computing RBP = YBS - CBS. 

EXAMPLE: _________

**Data Sources**
Kalshi: All forecasts began from Kalshi market prices. A set of anchors was pulled from Kalshi for every match to "anchor" each forecast with liquid market prices. The anchors included each team's win price, draw price, each team scoring 1+ goal, match having 1+ goal, and both teams scoring, among other anchors (full set of anchors in model file). These anchors were used as inputs to the probability distributions utilized to model each question. 

FBref: FBref was used for to reasons: to blend WC2026 team statistics with Kalshi prices and to model questions that didn't have Kalshi markets. Questions like "Will there be 4+ cards in the match?" did not have a corresponding Kalshi market price, so I utilized each team's FBref statistics from past matches in WC2026 to model such questions (for example, if Sweden has played 2 matches in the group stage and is currently playing their 3rd, I would use card data from their first 2 matches to model a cards question). 

NOTE: the above FBref method only worked because I joined the competition when most teams were playing their 2nd group stage match, so at the very least I had data from their first group stage match. My thought process was that the matches in WC2026 were the best indicators for predicting statistics in future WC2026 matches (rather than using matches before WC2026, such as in WC Qualifying, since those would be against different teams and would not mirror the same conditions as the actual WC). Intuitively, my predictions became more accurate as the competition progressed since I had more WC2026 matches to use data from. But if had I joined from the beginning, I would have defaulted to using Kalshi prices (as well as sportsbooks like DraftKings and FanDuel) for liquid markets and would have estimated probabilities of questions not on Kalshi using matches from before the WC (but as close to the WC as possible) as well as other inputs before I had actual WC2026 match data.

**Modeling Approach**

My model used 3 distributions to model each question type:

| Question type | Approach | Why I chose it |
|---|---|---|
| Goals | Negative Binomial | Allowed variance greater than the mean |
| Corners, cards, shots | Poisson | Baseline model for count events |
| Comparative outcomes | Skellam | Modeled differences between independent Poisson counts |
