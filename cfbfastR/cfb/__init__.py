import pyarrow.parquet as pq
import pandas as pd
import json
from typing import List, Callable, Iterator, Union, Optional
from cfbfastR.config import CFB_BASE_URL, CFB_ROSTER_URL, CFB_TEAM_LOGO_URL, CFB_TEAM_SCHEDULE_URL, CFB_TEAM_INFO_URL
from cfbfastR.errors import SeasonNotFoundError
from cfbfastR.dl_utils import download

def load_cfb_pbp(seasons: List[int]) -> pd.DataFrame:
    """Load college football play by play data going back to 2003

    Example:
        `cfb_df = cfbfastR.cfb.load_cfb_pbp(seasons=range(2003,2021))`

    Args:
        seasons (list): Used to define different seasons. 2003 is the earliest available season.

    Returns:
        pd.DataFrame: Pandas dataframe containing the play-by-plays available for the requested seasons.

    Raises:
        ValueError: If `season` is less than 2003.
    """
    data = pd.DataFrame()
    for i in seasons:
        if int(i) < 2003:
            raise SeasonNotFoundError("season cannot be less than 2003")
        i_data = pd.read_parquet(CFB_BASE_URL.format(season=i), engine='auto', columns=None)
        data = data.append(i_data)
    #Give each row a unique index
    data.reset_index(drop=True, inplace=True)
    return data

def load_cfb_schedule(seasons: List[int]) -> pd.DataFrame:
    """Load college football schedule data

    Example:
        `cfb_df = cfbfastR.cfb.load_cfb_schedule(seasons=range(2002,2021))`

    Args:
        seasons (list): Used to define different seasons. 2002 is the earliest available season.

    Returns:
        pd.DataFrame: Pandas dataframe containing the schedule for the requested seasons.

    Raises:
        ValueError: If `season` is less than 2002.
    """
    data = pd.DataFrame()
    for i in seasons:
        if int(i) < 2002:
            raise SeasonNotFoundError("season cannot be less than 2002")
        i_data = pd.read_parquet(CFB_TEAM_SCHEDULE_URL.format(season = i), engine='auto', columns=None)
        data = data.append(i_data)
    #Give each row a unique index
    data.reset_index(drop=True, inplace=True)

    return data

def load_cfb_rosters(seasons: List[int]) -> pd.DataFrame:
    """Load roster data

    Example:
        `cfb_df = cfbfastR.cfb.load_cfb_rosters(seasons=range(2014,2021))`

    Args:
        seasons (list): Used to define different seasons. 2014 is the earliest available season.

    Returns:
        pd.DataFrame: Pandas dataframe containing rosters available for the requested seasons.

    Raises:
        ValueError: If `season` is less than 2014.
    """
    data = pd.DataFrame()
    for i in seasons:
        if int(i) < 2014:
            raise SeasonNotFoundError("season cannot be less than 2014")
        i_data = pd.read_parquet(CFB_ROSTER_URL.format(season = i), engine='auto', columns=None)
        data = data.append(i_data)
    #Give each row a unique index
    data.reset_index(drop=True, inplace=True)

    return data

def load_cfb_team_info(seasons: List[int]) -> pd.DataFrame:
    """Load college football team info

    Example:
        `cfb_df = cfbfastR.cfb.load_cfb_team_info(seasons=range(2002,2021))`

    Args:
        seasons (list): Used to define different seasons. 2002 is the earliest available season.

    Returns:
        pd.DataFrame: Pandas dataframe containing the team info available for the requested seasons.

    Raises:
        ValueError: If `season` is less than 2002.
    """
    data = pd.DataFrame()
    for i in seasons:
        if int(i) < 2002:
            raise SeasonNotFoundError("season cannot be less than 2002")
        i_data = pd.read_parquet(CFB_ROSTER_URL.format(season = i), engine='auto', columns=None)
        data = data.append(i_data)
    #Give each row a unique index
    data.reset_index(drop=True, inplace=True)

    return data

def cfb_teams() -> pd.DataFrame:
    """Load college football team ID information and logos

    Example:
        `cfb_df = cfbfastR.cfb.cfb_teams()`

    Args:

    Returns:
        pd.DataFrame: Pandas dataframe containing teams available for the requested seasons.
    """
    df = pd.read_csv(CFB_TEAM_LOGO_URL)
    return df

def cfb_calendar(season: int) -> pd.DataFrame:
    """cfb_calendar - look up the men's college football calendar for a given season

    Args:
        season (int): Used to define different seasons. 2002 is the earliest available season.

    Returns:
        pd.DataFrame: Pandas dataframe containing calendar dates for the requested season.

    Raises:
        ValueError: If `season` is less than 2002.
    """
    url = "http://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?dates={}".format(season)
    resp = download(url=url)
    txt = json.loads(resp)['leagues'][0]['calendar']
    reg = pd.DataFrame(txt[0]['entries'])
    post = pd.DataFrame(txt[1]['entries'])
    full_schedule = pd.concat([reg,post], ignore_index=True)
    full_schedule['season']=season
    return full_schedule
