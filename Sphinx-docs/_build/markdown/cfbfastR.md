# cfbfastR package

## Submodules

## cfbfastR.cfb module


### cfbfastR.cfb.cfb_teams()
Load college football team ID information and logos
Args:
Returns:

> team_df (pandas dataframe): Pandas dataframe containing
> teams available for the requested seasons.


### cfbfastR.cfb.load_cfb_pbp(seasons: List[int])
Load college football play by play data going back to 2003
Args:

> seasons (list): Used to define different seasons. 2003 is the earliest available season.

Returns:

    pbp_df (pandas dataframe): Pandas dataframe containing
    play-by-plays available for the requested seasons.

Raises:

    ValueError: If season is less than 2003.


### cfbfastR.cfb.load_cfb_rosters(seasons: List[int])
Load roster data
Args:

> seasons (list): Used to define different seasons. 2014 is the earliest available season.

Returns:

    roster_df (pandas dataframe): Pandas dataframe containing
    rosters available for the requested seasons.

Raises:

    ValueError: If season is less than 2014.


### cfbfastR.cfb.load_cfb_schedule(seasons: List[int])
Load college football schedule data
Args:

> seasons (list): Used to define different seasons. 2002 is the earliest available season.

Returns:

    schedule_df (pandas dataframe): Pandas dataframe containing the
    schedule for  the requested seasons.

Raises:

    ValueError: If season is less than 2002.


### cfbfastR.cfb.load_cfb_team_info(seasons: List[int])
Load college football team info
Args:

> seasons (list): Used to define different seasons. 2002 is the earliest available season.

Returns:

    team_info_df (pandas dataframe): Pandas dataframe containing the
    team info available for the requested seasons.

Raises:

    ValueError: If season is less than 2002.

## cfbfastR.config module

## cfbfastR.dl_utils module


### cfbfastR.dl_utils.download(url, num_retries=5)
## cfbfastR.errors module

Custom exceptions for cfbfastR module


### exception cfbfastR.errors.SeasonNotFoundError()
Bases: `Exception`

## cfbfastR.pbp module

## cfbfastR.schedule module


### cfbfastR.schedule.cfb_calendar(season: int)
## Module contents
