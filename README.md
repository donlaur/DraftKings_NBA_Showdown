# DraftKings_showdown

This is a lineup optimizer for the DraftKings NBA showdown games, using the DraftKings API. It basically brute solves the knapsack problem, but with players' salaries as the "weights" and their fantasy points as the "values."

I took it a step further and also used the NBA API. So the program pulls each player's game logs and calculates the last X games average fantasy points per game (fppg), as well as the season fppg against their upcoming opponent. The different adjusted fppg scores are then weighted and the lineup optimizer runs.

Playing live games with this program, I ended up slightly above break even over the span of three to four weeks.
