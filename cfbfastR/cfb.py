import pyarrow.parquet as pq
import pandas as pd
from typing import List, Callable, Iterator, Union, Optional
from cfbfastR.config import CFB_BASE_URL, CFB_ROSTER_URL, CFB_TEAM_LOGO_URL, CFB_TEAM_SCHEDULE_URL, CFB_TEAM_INFO_URL
from cfbfastR.errors import SeasonNotFoundError

def load_cfb_pbp(years: List[int]) -> pd.DataFrame:
    """
    Load college football play by play data going back to 2003
    Args:
        years (list): Used to define different seasons. 2003 is the earliest available season.
    Returns:
        pbp_df (pandas dataframe): Pandas dataframe containing
        play-by-plays available for the requested seasons.
    Raises:
        ValueError: If `year` is less than 2003.
    """
    data = pd.DataFrame()
    for i in years:
        if int(i) < 2003:
            raise SeasonNotFoundError("season cannot be less than 2003")
        i_data = pd.read_parquet(CFB_BASE_URL.format(year=i), engine='auto', columns=None, 
        use_nullable_dtypes=False)
        data = data.append(i_data)
    #Give each row a unique index
    data.reset_index(drop=True, inplace=True)
    return data

def load_cfb_schedule(years: List[int]) -> pd.DataFrame:
    """
    Load college football schedule data
    Args:
        years (list): Used to define different seasons. 2002 is the earliest available season.
    Returns:
        schedule_df (pandas dataframe): Pandas dataframe containing the
        schedule for  the requested seasons.
    Raises:
        ValueError: If `year` is less than 2002.
    """
    data = pd.DataFrame()
    for i in years:
        if int(i) < 2002:
            raise SeasonNotFoundError("season cannot be less than 2002")
        i_data = pd.read_parquet(CFB_TEAM_SCHEDULE_URL.format(year = i), engine='auto', columns=None, 
        use_nullable_dtypes=False)
        data = data.append(i_data)
    #Give each row a unique index
    data.reset_index(drop=True, inplace=True)

    return data

def load_cfb_rosters(years: List[int]) -> pd.DataFrame:
    """
    Load roster data
    Args:
        years (list): Used to define different seasons. 2014 is the earliest available season.
    Returns:
        roster_df (pandas dataframe): Pandas dataframe containing
        rosters available for the requested seasons.
    Raises:
        ValueError: If `year` is less than 2014.
    """
    data = pd.DataFrame()
    for i in years:
        if int(i) < 2014:
            raise SeasonNotFoundError("season cannot be less than 2014")
        i_data = pd.read_parquet(CFB_ROSTER_URL.format(year = i), engine='auto', columns=None, 
        use_nullable_dtypes=False)
        data = data.append(i_data)
    #Give each row a unique index
    data.reset_index(drop=True, inplace=True)

    return data

def cfb_teams() -> pd.DataFrame:
    """
    Load college football team ID information and logos
    Args:
    Returns:
        team_df (pandas dataframe): Pandas dataframe containing
        teams available for the requested seasons.
    """
    df = pd.read_csv(CFB_TEAM_LOGO_URL)
    return df

def load_cfb_team_info(years: List[int]) -> pd.DataFrame:
    """
    Load college football team info
    Args:
        years (list): Used to define different seasons. 2002 is the earliest available season.
    Returns:
        team_info_df (pandas dataframe): Pandas dataframe containing the
        team info available for the requested seasons.
    Raises:
        ValueError: If `year` is less than 2002.
    """
    data = pd.DataFrame()
    for i in years:
        if int(i) < 2002:
            raise SeasonNotFoundError("season cannot be less than 2002")
        i_data = pd.read_parquet(CFB_ROSTER_URL.format(year = i), engine='auto', columns=None, 
        use_nullable_dtypes=False)
        data = data.append(i_data)
    #Give each row a unique index
    data.reset_index(drop=True, inplace=True)

    return data

