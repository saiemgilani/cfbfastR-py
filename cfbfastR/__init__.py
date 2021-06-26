import pyarrow.parquet as pq
import pandas as pd
from typing import Callable, Iterator, Union, Optional, List
from cfbfastR.config import CFB_BASE_URL, CFB_ROSTER_URL, CFB_TEAM_LOGO_URL, CFB_TEAM_SCHEDULE_URL, CFB_TEAM_INFO_URL
from cfbfastR.errors import SeasonNotFoundError

def load_cfb_pbp(years: List[int]) -> pd.DataFrame:
    """
    Load college football play by play data going back to 2003
    """
    data = pd.DataFrame()
    for i in years:
        i_data = pd.read_parquet(CFB_BASE_URL.format(year=i), engine='auto', columns=None, 
        use_nullable_dtypes=False)
        data = data.append(i_data)
    #Give each row a unique index
    data.reset_index(drop=True, inplace=True)
    return data

def load_cfb_schedule(years: List[int]) -> pd.DataFrame:
    """
    Load college football schedule data
    """
    data = pd.DataFrame()
    for i in years:
        i_data = pd.read_parquet(CFB_TEAM_SCHEDULE_URL.format(year = i), engine='auto', columns=None, 
        use_nullable_dtypes=False)
        data = data.append(i_data)
    #Give each row a unique index
    data.reset_index(drop=True, inplace=True)

    return data

def load_cfb_rosters(years: List[int]) -> pd.DataFrame:
    """
    Load roster data
    """
    data = pd.DataFrame()
    for i in years:
        i_data = pd.read_parquet(CFB_ROSTER_URL.format(year = i), engine='auto', columns=None, 
        use_nullable_dtypes=False)
        data = data.append(i_data)
    #Give each row a unique index
    data.reset_index(drop=True, inplace=True)

    return data

def cfb_teams() -> pd.DataFrame:
    """
    Load college football team ID information and logos
    """
    df = pd.read_csv(CFB_TEAM_LOGO_URL)
    return df

def load_cfb_team_info(years: List[int]) -> pd.DataFrame:
    """
    Load college football team info
    """
    data = pd.DataFrame()
    for i in years:
        i_data = pd.read_parquet(CFB_ROSTER_URL.format(year = i), engine='auto', columns=None, 
        use_nullable_dtypes=False)
        data = data.append(i_data)
    #Give each row a unique index
    data.reset_index(drop=True, inplace=True)

    return data

