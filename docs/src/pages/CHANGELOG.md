## 0.0.10 Release: July 6, 2021
- Fix list/int arguments to accept either.

### Add nflfastR data functions

- Function added: `load_nfl_pbp(seasons: List[int]) -> pd.DataFrame`
- Function added: `load_nfl_schedule(seasons: List[int]) -> pd.DataFrame`
- Function added: `load_nfl_rosters(seasons: List[int]) -> pd.DataFrame`
- Function added: `load_nfl_player_stats() -> pd.DataFrame`
- Function added: `nfl_teams() -> pd.DataFrame`


## 0.0.8 Release: July 4, 2021
- Remove nullable dtype argument from `pyarrow` calls

## 0.0.7 Release: July 2, 2021
- Updated documentation for all functions
- Created documentation website at [https://cfbfastR-py.sportsdataverse.org/](https://cfbfastR.sportsdataverse.org/)
- Fix issue with `season` replacing `year` in `config.py`

## 0.0.2 Release: June 26, 2021
- Function added: `load_cfb_pbp(seasons: List[int]) -> pd.DataFrame`
- Function added: `cfb_calendar(season: int) -> pd.DataFrame`
- Function added: `load_cfb_schedule(seasons: List[int]) -> pd.DataFrame`
- Function added: `load_cfb_rosters(seasons: List[int]) -> pd.DataFrame`
- Function added: `cfb_teams() -> pd.DataFrame`
- Function added: `load_cfb_team_info(seasons: List[int]) -> pd.DataFrame`

## 0.0.1 Release: June 26, 2021
- f'in round
- findin' out