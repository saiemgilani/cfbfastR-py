import pyarrow.parquet as pq
import pandas as pd
import json
from typing import List, Callable, Iterator, Union, Optional
from cfbfastR.config import NFL_BASE_URL, NFL_ROSTER_URL, NFL_TEAM_LOGO_URL, NFL_TEAM_SCHEDULE_URL, CFB_TEAM_INFO_URL
from cfbfastR.errors import SeasonNotFoundError
from cfbfastR.dl_utils import download

def load_nfl_pbp(seasons: List[int]) -> pd.DataFrame:
    """Load NFL play by play data going back to 1999

    Example:
        `nfl_df = cfbfastR.nfl.load_nfl_pbp(seasons=range(1999,2021))`

    Args:
        seasons (list): Used to define different seasons. 1999 is the earliest available season.

    Returns:
        pd.DataFrame: Pandas dataframe containing the play-by-plays available for the requested seasons.

    Raises:
        ValueError: If `season` is less than 1999.
    """
    data = pd.DataFrame()
    if type(seasons) is int:
        seasons = [seasons]
    for i in seasons:
        if int(i) < 1999:
            raise SeasonNotFoundError("season cannot be less than 1999")
        i_data = pd.read_parquet(NFL_BASE_URL.format(season=i), engine='auto', columns=None)
        data = data.append(i_data)
    #Give each row a unique index
    data.reset_index(drop=True, inplace=True)
    return data

def load_nfl_schedule(seasons: List[int]) -> pd.DataFrame:
    """Load NFL schedule data

    Example:
        `nfl_df = cfbfastR.nfl.load_nfl_schedule(seasons=range(1999,2021))`

    Args:
        seasons (list): Used to define different seasons. 1999 is the earliest available season.

    Returns:
        pd.DataFrame: Pandas dataframe containing the schedule for the requested seasons.

    Raises:
        ValueError: If `season` is less than 1999.
    """
    data = pd.DataFrame()
    if type(seasons) is int:
        seasons = [seasons]
    for i in seasons:
        if int(i) < 1999:
            raise SeasonNotFoundError("season cannot be less than 1999")
        i_data = pd.read_parquet(NFL_TEAM_SCHEDULE_URL.format(season = i), engine='auto', columns=None)
        data = data.append(i_data)
    #Give each row a unique index
    data.reset_index(drop=True, inplace=True)

    return data

def load_nfl_player_stats() -> pd.DataFrame:
    """Load NFL player stats data

    Example:
        `nfl_df = cfbfastR.nfl.load_nfl_player_stats()`

    Args:

    Returns:
        pd.DataFrame: Pandas dataframe containing player stats.
    """
    data = pd.DataFrame()
    i_data = pd.read_parquet(NFL_PLAYER_STATS_URL.format(season = i), engine='auto', columns=None)
    data = data.append(i_data)
    #Give each row a unique index
    data.reset_index(drop=True, inplace=True)

    return data

def load_nfl_rosters(seasons: List[int]) -> pd.DataFrame:
    """Load NFL roster data

    Example:
        `nfl_df = cfbfastR.nfl.load_nfl_rosters(seasons=range(1999,2021))`

    Args:
        seasons (list): Used to define different seasons. 1999 is the earliest available season.

    Returns:
        pd.DataFrame: Pandas dataframe containing rosters available for the requested seasons.

    Raises:
        ValueError: If `season` is less than 1999.
    """
    data = pd.DataFrame()
    if type(seasons) is int:
        seasons = [seasons]
    for i in seasons:
        if int(i) < 1999:
            raise SeasonNotFoundError("season cannot be less than 1999")
        i_data = pd.read_parquet(NFL_ROSTER_URL.format(season = i), engine='auto', columns=None)
        data = data.append(i_data)
    #Give each row a unique index
    data.reset_index(drop=True, inplace=True)

    return data

def nfl_teams() -> pd.DataFrame:
    """Load NFL team ID information and logos

    Example:
        `nfl_df = cfbfastR.nfl.nfl_teams()`

    Args:

    Returns:
        pd.DataFrame: Pandas dataframe containing teams available for the requested seasons.
    """
    df = pd.read_csv(NFL_TEAM_LOGO_URL)
    return df