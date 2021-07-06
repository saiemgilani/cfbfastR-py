---
title: Load NFL Rosters
sidebar_label: Load NFL Rosters
---

### cfbfastR.nfl.load_nfl_rosters(seasons: List[int])
Load roster data

Example:

    nfl_df = cfbfastR.nfl.load_nfl_rosters(seasons=range(1999,2021))

Args:

    seasons (list): Used to define different seasons. 1999 is the earliest available season.

Returns:

    pd.DataFrame: Pandas dataframe containing rosters available for the requested seasons.

Raises:

    ValueError: If season is less than 1999.


