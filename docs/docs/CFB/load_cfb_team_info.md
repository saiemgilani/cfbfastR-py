---
title: Load CFB Team Info
sidebar_label: Load CFB Team Info
---

### cfbfastR.cfb.load_cfb_team_info(seasons: List[int])
Load college football team info

Args:

    seasons (list): Used to define different seasons. 2002 is the earliest available season.

Returns:

    pd.DataFrame: Pandas dataframe containing the team info available for the requested seasons.

Raises:

    ValueError: If season is less than 2002.
