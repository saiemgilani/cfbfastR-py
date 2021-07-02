from numpy.core.fromnumeric import mean
import pandas as pd
import numpy as np
import xgboost as xgb
import os
import re
import json
import time
import http
import urllib
from urllib.error import URLError, HTTPError, ContentTooShortError
from datetime import datetime
from itertools import chain, starmap

ep_class_to_score_mapping = {
    0: 7,
    1: -7,
    2: 3,
    3: -3,
    4: 2,
    5: -2,
    6: 0
}

# "td" : float(p[0]),
# "opp_td" : float(p[1]),
# "fg" : float(p[2]),
# "opp_fg" : float(p[3]),
# "safety" : float(p[4]),
# "opp_safety" : float(p[5]),
# "no_score" : float(p[6])

ep_model = xgb.Booster({'nthread': 4})  # init model
ep_model.load_model('models/xgb_ep_model.model')

wp_model = xgb.Booster({'nthread': 4})  # init model
wp_model.load_model('models/xgb_wp_spread_model.model')

wp_start_touchback_columns = [
    # "start.posteam_receives_2H_kickoff",
    "start.spread_time",
    "start.game_seconds_remaining",
    "start.half_seconds_remaining",
    "start.ExpScoreDiff_Time_Ratio_touchback",
    "start.posteam_score_differential",
    "start.down",
    "start.ydstogo",
    "start.yardline_100.touchback",
    # "start.posteam_type",
    "start.posteamTimeouts",
    "start.defteamTimeouts" #,
    # "qtr"
]
wp_start_columns = [
    # "start.posteam_receives_2H_kickoff",
    "start.spread_time",
    "start.game_seconds_remaining",
    "start.half_seconds_remaining",
    "start.ExpScoreDiff_Time_Ratio",
    "start.posteam_score_differential",
    "start.down",
    "start.ydstogo",
    "start.yardline_100",
    # "start.posteam_type",
    "start.posteamTimeouts",
    "start.defteamTimeouts" #,
    # "qtr"
]
wp_end_columns = [
    # "end.posteam_receives_2H_kickoff",
    "end.spread_time",
    "end.game_seconds_remaining",
    "end.half_seconds_remaining",
    "end.ExpScoreDiff_Time_Ratio",
    "end.posteam_score_differential",
    "end.down",
    "end.ydstogo",
    "end.yardline_100",
    # "end.posteam_type",
    "end.posteamTimeouts",
    "end.defteamTimeouts" #,
    # "qtr"
]

ep_start_touchback_columns = [
    "start.half_seconds_remaining",
    "start.yardline_100.touchback",
    "ydstogo",
    "down_1",
    "down_2",
    "down_3",
    "down_4",
    "start.posteam_score_differential"
]
ep_start_columns = [
    "start.half_seconds_remaining",
    "start.yardline_100",
    "start.ydstogo",
    "down_1",
    "down_2",
    "down_3",
    "down_4",
    "start.posteam_score_differential"
]
ep_end_columns = [
    "end.half_seconds_remaining",
    "end.yardline_100",
    "end.ydstogo",
    "down_1_end",
    "down_2_end",
    "down_3_end",
    "down_4_end",
    "end.posteam_score_differential"
]

ep_final_names = [
    "half_seconds_remaining",
    "yardline_100",
    "ydstogo",
    "down_1",
    "down_2",
    "down_3",
    "down_4",
    "posteam_score_differential"
]
wp_final_names = [
    # "posteam_receives_2H_kickoff",
    "spread_time",
    "game_seconds_remaining",
    "half_seconds_remaining",
    "ExpScoreDiff_Time_Ratio",
    "posteam_score_differential",
    "down",
    "ydstogo",
    "yardline_100",
    # "posteam_type",
    "posteam_timeouts",
    "defteam_timeouts" #,
    # "qtr"
]

    #-------Play type vectors-------------
scores_vec = [
    "Blocked Punt Touchdown",
    "Blocked Punt (Safety)",
    "Punt (Safety)",
    "Blocked Field Goal Touchdown",
    "Missed Field Goal Return Touchdown",
    "Fumble Recovery (Opponent) Touchdown",
    "Fumble Return Touchdown",
    "Interception Return Touchdown",
    "Pass Interception Return Touchdown",
    "Punt Touchdown",
    "Punt Return Touchdown",
    "Sack Touchdown",
    "Uncategorized Touchdown",
    "Defensive 2pt Conversion",
    "Uncategorized",
    "Two Point Rush",
    "Safety",
    "Penalty (Safety)",
    "Punt Team Fumble Recovery Touchdown",
    "Kickoff Team Fumble Recovery Touchdown",
    "Kickoff (Safety)",
    "Passing Touchdown",
    "Rushing Touchdown",
    "Field Goal Good",
    "Pass Reception Touchdown",
    "Fumble Recovery (Own) Touchdown"
]
defense_score_vec = [
    "Blocked Punt Touchdown",
    "Blocked Field Goal Touchdown",
    "Missed Field Goal Return Touchdown",
    "Punt Return Touchdown",
    "Fumble Recovery (Opponent) Touchdown",
    "Fumble Return Touchdown",
    "Kickoff Return Touchdown",
    "Defensive 2pt Conversion",
    "Safety",
    "Sack Touchdown",
    "Interception Return Touchdown",
    "Pass Interception Return Touchdown",
    "Uncategorized Touchdown"
]
turnover_vec = [
    "Blocked Field Goal",
    "Blocked Field Goal Touchdown",
    "Blocked Punt",
    "Blocked Punt Touchdown",
    "Field Goal Missed",
    "Missed Field Goal Return",
    "Missed Field Goal Return Touchdown",
    "Fumble Recovery (Opponent)",
    "Fumble Recovery (Opponent) Touchdown",
    "Fumble Return Touchdown",
    "Defensive 2pt Conversion",
    "Interception",
    "Interception Return",
    "Interception Return Touchdown",
    "Pass Interception Return",
    "Pass Interception Return Touchdown",
    "Kickoff Team Fumble Recovery",
    "Kickoff Team Fumble Recovery Touchdown",
    "Punt Touchdown",
    "Punt Return Touchdown",
    "Sack Touchdown",
    "Uncategorized Touchdown"
]
normalplay = [
    "Rush",
    "Pass",
    "Pass Reception",
    "Pass Incompletion",
    "Pass Completion",
    "Sack",
    "Fumble Recovery (Own)"
]
penalty = [
    'Penalty',
    'Penalty (Kickoff)',
    'Penalty (Safety)'
]
offense_score_vec = [
    "Passing Touchdown",
    "Rushing Touchdown",
    "Field Goal Good",
    "Pass Reception Touchdown",
    "Fumble Recovery (Own) Touchdown",
    "Punt Touchdown", #<--- Punting Team recovers the return team fumble and scores
    "Punt Team Fumble Recovery Touchdown",
    "Kickoff Touchdown", #<--- Kickoff Team recovers the return team fumble and scores
    "Kickoff Team Fumble Recovery Touchdown"
]
punt_vec = [
    "Blocked Punt",
    "Blocked Punt Touchdown",
    "Blocked Punt (Safety)",
    "Punt (Safety)",
    "Punt",
    "Punt Return",
    "Punt Touchdown",
    "Punt Team Fumble Recovery",
    "Punt Team Fumble Recovery Touchdown",
    "Punt Return Touchdown"
]
kickoff_vec = [
    "Kickoff",
    "Kickoff Return (Offense)",
    "Kickoff Return Touchdown",
    "Kickoff Touchdown",
    "Kickoff Team Fumble Recovery",
    "Kickoff Team Fumble Recovery Touchdown",
    "Kickoff (Safety)",
    "Penalty (Kickoff)"
]
int_vec = [
    "Interception",
    "Interception Return",
    "Interception Return Touchdown",
    "Pass Interception",
    "Pass Interception Return",
    "Pass Interception Return Touchdown"
]
end_change_vec = [
    "Blocked Field Goal",
    "Blocked Field Goal Touchdown",
    "Field Goal Missed",
    "Missed Field Goal Return",
    "Missed Field Goal Return Touchdown",
    "Blocked Punt",
    "Blocked Punt Touchdown",
    "Punt",
    "Punt Return",
    "Punt Touchdown",
    "Punt Return Touchdown",
    "Kickoff Team Fumble Recovery",
    "Kickoff Team Fumble Recovery Touchdown",
    "Fumble Recovery (Opponent)",
    "Fumble Recovery (Opponent) Touchdown",
    "Fumble Return Touchdown",
    "Sack Touchdown",
    "Defensive 2pt Conversion",
    "Interception",
    "Interception Return",
    "Interception Return Touchdown",
    "Pass Interception Return",
    "Pass Interception Return Touchdown",
    "Uncategorized Touchdown"
]
kickoff_turnovers = [
    "Kickoff Team Fumble Recovery",
    "Kickoff Team Fumble Recovery Touchdown"
]
    #---------------------------------
class PlayProcess(object):

    gameId = 0
    ran_pipeline = False
    ran_EP_pipeline = False
    ran_cleaning_pipeline = False
    path_to_json = '/'

    def __init__(self, gameId = 0, path_to_json = '/'):
        self.gameId = int(gameId)
        self.ran_pipeline = False
        self.ran_EP_pipeline = False
        self.ran_clean_pipeline = False
        self.path_to_json = path_to_json

    def download(self, url, num_retries=5):
        try:
            html = urllib.request.urlopen(url).read()
        except (URLError, HTTPError, ContentTooShortError, http.client.HTTPException, http.client.IncompleteRead) as e:
            print('Download error:', url)
            html = None
            if num_retries > 0:
                if hasattr(e, 'code') and 500 <= e.code < 600:
                    time.sleep(10)
                    # recursively retry 5xx HTTP errors
                    return self.download(url, num_retries - 1)
            if num_retries > 0:
                if e == http.client.IncompleteRead:
                    time.sleep(10)
                    return self.download(url, num_retries - 1)
        return html

    def cfb_pbp(self):
        """
            cfb_pbp()
            Pull the game by id
            Data from API endpoints:
                * college-football/playbyplay
                * college-football/summary
        """
        # play by play
        pbp_url = "http://cdn.espn.com/core/college-football/playbyplay?gameId={}&xhr=1&render=false&userab=18".format(self.gameId)
        pbp_resp = self.download(url=pbp_url)
        pbp_txt = {}
        pbp_txt['scoringPlays'] = np.array([])
        pbp_txt['standings'] = np.array([])
        pbp_txt['videos'] = np.array([])
        pbp_txt['broadcasts'] = np.array([])
        pbp_txt['winprobability'] = np.array([])
        pbp_txt['espnWP'] = np.array([])
        pbp_txt['gameInfo'] = np.array([])
        pbp_txt['season'] = np.array([])

        pbp_txt = json.loads(pbp_resp)['gamepackageJSON']
        pbp_txt['odds'] = np.array([])
        pbp_txt['predictor'] = {}
        pbp_txt['againstTheSpread'] = np.array([])
        pbp_txt['pickcenter'] = np.array([])

        pbp_txt['timeouts'] = {}
        # summary endpoint for pickcenter array
        summary_url = "http://site.api.espn.com/apis/site/v2/sports/football/college-football/summary?event={}".format(self.gameId)
        summary_resp = self.download(summary_url)
        summary = json.loads(summary_resp)
        summary_txt = summary['pickcenter']
        summary_ats = summary['againstTheSpread']
        summary_odds = summary['odds']
        if 'againstTheSpread' in summary.keys():
            summary_ats = summary['againstTheSpread']
        else:
            summary_ats = np.array([])
        if 'odds' in summary.keys():
            summary_odds = summary['odds']
        else:
            summary_odds = np.array([])
        if 'predictor' in summary.keys():
            summary_predictor = summary['predictor']
        else:
            summary_predictor = {}
        # ESPN's win probability
        wp = "winprobability"
        if wp in summary.keys():
            espnWP = summary["winprobability"]
        else:
            espnWP = np.array([])

        if 'news' in pbp_txt.keys():
            del pbp_txt['news']
        if 'shop' in pbp_txt.keys():
            del pbp_txt['shop']
        pbp_txt['gameInfo'] = pbp_txt['header']['competitions'][0]
        pbp_txt['season'] = pbp_txt['header']['season']
        pbp_txt['playByPlaySource'] = pbp_txt['header']['competitions'][0]['playByPlaySource']
        pbp_txt['pickcenter'] = summary_txt
        pbp_txt['againstTheSpread'] = summary_ats
        pbp_txt['odds'] = summary_odds
        pbp_txt['predictor'] = summary_predictor
        pbp_txt['espnWP'] = espnWP
        # Home and Away identification variables
        homeTeamId = int(pbp_txt['header']['competitions'][0]['competitors'][0]['team']['id'])
        awayTeamId = int(pbp_txt['header']['competitions'][0]['competitors'][1]['team']['id'])
        homeTeamMascot = str(pbp_txt['header']['competitions'][0]['competitors'][0]['team']['name'])
        awayTeamMascot = str(pbp_txt['header']['competitions'][0]['competitors'][1]['team']['name'])
        homeTeamName = str(pbp_txt['header']['competitions'][0]['competitors'][0]['team']['location'])
        awayTeamName = str(pbp_txt['header']['competitions'][0]['competitors'][1]['team']['location'])
        homeTeamAbbrev = str(pbp_txt['header']['competitions'][0]['competitors'][0]['team']['abbreviation'])
        awayTeamAbbrev = str(pbp_txt['header']['competitions'][0]['competitors'][1]['team']['abbreviation'])
        homeTeamNameAlt = re.sub("Stat(.+)", "St", str(homeTeamName))
        awayTeamNameAlt = re.sub("Stat(.+)", "St", str(awayTeamName))

        if len(pbp_txt['pickcenter']) > 1:
            if 'spread' in pbp_txt['pickcenter'][1].keys():
                gameSpread =  pbp_txt['pickcenter'][1]['spread']
                homeFavorite = pbp_txt['pickcenter'][1]['homeTeamOdds']['favorite']
                gameSpreadAvailable = True
            else:
                gameSpread =  pbp_txt['pickcenter'][0]['spread']
                homeFavorite = pbp_txt['pickcenter'][0]['homeTeamOdds']['favorite']
                gameSpreadAvailable = True

        else:
            gameSpread = 2.5
            homeFavorite = True
            gameSpreadAvailable = False
        # negotiating the drive meta keys into columns after unnesting drive plays
        # concatenating the previous and current drives categories when necessary
        if pbp_txt['playByPlaySource'] != "none":
            if 'drives' in pbp_txt.keys():
                pbp_txt['plays'] = pd.DataFrame()
                prev_drives = pd.json_normalize(
                    data = pbp_txt['drives']['previous'],
                    record_path = 'plays',
                    meta = ['id', 'displayResult','isScore',
                            ['team','shortDisplayName'],
                            ['team','displayName'],
                            ['team','name'],
                            ['team','abbreviation'],
                            'yards','offensivePlays','result',
                            'description',
                            'shortDisplayResult',
                            ['timeElapsed','displayValue'],
                            ['start','period','number'],
                            ['start','period','type'],
                            ['start','yardLine'],
                            ['start','clock','displayValue'],
                            ['start','text'],
                            ['end','period','number'],
                            ['end','period','type'],
                            ['end','yardLine'],
                            ['end','clock','displayValue']],
                    meta_prefix = 'drive.', errors = 'ignore')

                if len(pbp_txt['drives'].keys()) > 1:
                    curr_drives = pd.json_normalize(
                        data = pbp_txt['drives']['current'],
                        record_path = 'plays',
                        meta = ['id', 'displayResult','isScore',
                                ['team','shortDisplayName'],
                                ['team','displayName'],
                                ['team','name'],
                                ['team','abbreviation'],
                                'yards','offensivePlays','result',
                                'description',
                                'shortDisplayResult',
                                ['timeElapsed','displayValue'],
                                ['start','period','number'],
                                ['start','period','type'],
                                ['start','yardLine'],
                                ['start','clock','displayValue'],
                                ['start','text'],
                                ['end','period','number'],
                                ['end','period','type'],
                                ['end','yardLine'],
                                ['end','clock','displayValue']],
                        meta_prefix = 'drive.', errors = 'ignore')
                    pbp_txt['plays'] = pd.concat([curr_drives, prev_drives], ignore_index=True)
                else:
                    pbp_txt['plays'] = prev_drives

                pbp_txt['plays']['season'] = pbp_txt['header']['season']['year']
                pbp_txt['plays']['seasonType'] = pbp_txt['header']['season']['type']
                pbp_txt['plays']["awayTeamId"] = awayTeamId
                pbp_txt['plays']["awayTeamName"] = str(awayTeamName)
                pbp_txt['plays']["awayTeamMascot"] = str(awayTeamMascot)
                pbp_txt['plays']["awayTeamAbbrev"] = str(awayTeamAbbrev)
                pbp_txt['plays']["awayTeamNameAlt"] = str(awayTeamNameAlt)
                pbp_txt['plays']["homeTeamId"] = homeTeamId
                pbp_txt['plays']["homeTeamName"] = str(homeTeamName)
                pbp_txt['plays']["homeTeamMascot"] = str(homeTeamMascot)
                pbp_txt['plays']["homeTeamAbbrev"] = str(homeTeamAbbrev)
                pbp_txt['plays']["homeTeamNameAlt"] = str(homeTeamNameAlt)
                # Spread definition
                pbp_txt['plays']["homeTeamSpread"] = 2.5
                pbp_txt['plays']["gameSpread"] = abs(gameSpread)
                pbp_txt['plays']["homeTeamSpread"] = np.where(homeFavorite == True, abs(gameSpread), -1*abs(gameSpread))
                pbp_txt['homeTeamSpread'] = np.where(homeFavorite == True, abs(gameSpread), -1*abs(gameSpread))
                pbp_txt['plays']["homeFavorite"] = homeFavorite
                pbp_txt['plays']["gameSpread"] = gameSpread
                pbp_txt['plays']["gameSpreadAvailable"] = gameSpreadAvailable
                pbp_txt['plays'] = pbp_txt['plays'].to_dict(orient='records')
                pbp_txt['plays'] = pd.DataFrame(pbp_txt['plays'])
                pbp_txt['plays']['season'] = pbp_txt['header']['season']['year']
                pbp_txt['plays']['seasonType'] = pbp_txt['header']['season']['type']
                pbp_txt['plays']['week'] = pbp_txt['header']['week']
                pbp_txt['plays']['game_id'] = int(self.gameId)
                pbp_txt['plays']["homeTeamId"] = homeTeamId
                pbp_txt['plays']["awayTeamId"] = awayTeamId
                pbp_txt['plays']["homeTeamName"] = str(homeTeamName)
                pbp_txt['plays']["awayTeamName"] = str(awayTeamName)
                pbp_txt['plays']["homeTeamMascot"] = str(homeTeamMascot)
                pbp_txt['plays']["awayTeamMascot"] = str(awayTeamMascot)
                pbp_txt['plays']["homeTeamAbbrev"] = str(homeTeamAbbrev)
                pbp_txt['plays']["awayTeamAbbrev"] = str(awayTeamAbbrev)
                pbp_txt['plays']["homeTeamNameAlt"] = str(homeTeamNameAlt)
                pbp_txt['plays']["awayTeamNameAlt"] = str(awayTeamNameAlt)
                pbp_txt['plays']['period.number'] = pbp_txt['plays']['period.number'].apply(lambda x: int(x))
                pbp_txt['plays']['qtr'] = pbp_txt['plays']['period.number'].apply(lambda x: int(x))

                #----- Figuring out Timeouts ---------
                pbp_txt['timeouts'] = {}
                pbp_txt['timeouts'][homeTeamId] = {"1": [], "2": []}
                pbp_txt['timeouts'][awayTeamId] = {"1": [], "2": []}

                pbp_txt['plays']["homeTeamSpread"] = 2.5
                if len(pbp_txt['pickcenter']) > 1:
                    if 'spread' in pbp_txt['pickcenter'][1].keys():
                        gameSpread =  pbp_txt['pickcenter'][1]['spread']
                        homeFavorite = pbp_txt['pickcenter'][1]['homeTeamOdds']['favorite']
                        gameSpreadAvailable = True
                    else:
                        gameSpread =  pbp_txt['pickcenter'][0]['spread']
                        homeFavorite = pbp_txt['pickcenter'][0]['homeTeamOdds']['favorite']
                        gameSpreadAvailable = True

                else:
                    gameSpread = 2.5
                    homeFavorite = True
                    gameSpreadAvailable = False
                pbp_txt['plays']["gameSpread"] = abs(gameSpread)
                pbp_txt['plays']["gameSpreadAvailable"] = gameSpreadAvailable
                pbp_txt['plays']["homeTeamSpread"] = np.where(homeFavorite == True, abs(gameSpread), -1*abs(gameSpread))
                pbp_txt['homeTeamSpread'] = np.where(homeFavorite == True, abs(gameSpread), -1*abs(gameSpread))
                pbp_txt['plays']["homeFavorite"] = homeFavorite
                pbp_txt['plays']["gameSpread"] = gameSpread
                pbp_txt['plays']["homeFavorite"] = homeFavorite

                #----- Time ---------------
                pbp_txt['plays']['time'] = pbp_txt['plays']['clock.displayValue']
                pbp_txt['plays']['clock.mm'] = pbp_txt['plays']['clock.displayValue'].str.split(pat=':')
                pbp_txt['plays'][['clock.minutes','clock.seconds']] = pbp_txt['plays']['clock.mm'].to_list()
                pbp_txt['plays']['half'] = np.where(pbp_txt['plays']['qtr'] <= 2, "1","2")
                pbp_txt['plays']['game_half'] = np.where(pbp_txt['plays']['qtr'] <= 2, "1","2")
                pbp_txt['plays']['lag_qtr'] = pbp_txt['plays']['qtr'].shift(1)
                pbp_txt['plays']['lead_qtr'] = pbp_txt['plays']['qtr'].shift(-1)
                pbp_txt['plays']['lag_game_half'] = pbp_txt['plays']['game_half'].shift(1)
                pbp_txt['plays']['lead_game_half'] = pbp_txt['plays']['game_half'].shift(-1)
                pbp_txt['plays']['start.quarter_seconds_remaining'] = 60*pbp_txt['plays']['clock.minutes'].astype(int) + pbp_txt['plays']['clock.seconds'].astype(int)
                pbp_txt['plays']['start.half_seconds_remaining'] = np.where(
                    pbp_txt['plays']['qtr'].isin([1,3]),
                    900 + 60*pbp_txt['plays']['clock.minutes'].astype(int) + pbp_txt['plays']['clock.seconds'].astype(int),
                    60*pbp_txt['plays']['clock.minutes'].astype(int) + pbp_txt['plays']['clock.seconds'].astype(int)
                )
                pbp_txt['plays']['start.game_seconds_remaining'] = np.select(
                    [
                        pbp_txt['plays']['qtr'] == 1,
                        pbp_txt['plays']['qtr'] == 2,
                        pbp_txt['plays']['qtr'] == 3,
                        pbp_txt['plays']['qtr'] == 4
                    ],
                    [
                        2700 + 60*pbp_txt['plays']['clock.minutes'].astype(int) + pbp_txt['plays']['clock.seconds'].astype(int),
                        1800 + 60*pbp_txt['plays']['clock.minutes'].astype(int) + pbp_txt['plays']['clock.seconds'].astype(int),
                        900 + 60*pbp_txt['plays']['clock.minutes'].astype(int) + pbp_txt['plays']['clock.seconds'].astype(int),
                        60*pbp_txt['plays']['clock.minutes'].astype(int) + pbp_txt['plays']['clock.seconds'].astype(int)
                    ], default = 60*pbp_txt['plays']['clock.minutes'].astype(int) + pbp_txt['plays']['clock.seconds'].astype(int)
                )
                # Pos Team - Start and End Id
                pbp_txt['plays']['game_play_number'] = np.arange(len(pbp_txt['plays']))+1
                pbp_txt['plays']['text'] = pbp_txt['plays']['text'].astype(str)
                pbp_txt['plays']['id'] = pbp_txt['plays']['id'].apply(lambda x: int(x))
                pbp_txt['plays']["start.team.id"] = pbp_txt['plays']["start.team.id"].fillna(method='ffill').apply(lambda x: int(x))
                if "end.team.id" not in pbp_txt['plays'].keys():
                    pbp_txt['plays']['end.team.id'] = pbp_txt['plays']["start.team.id"]
                pbp_txt['plays']["end.team.id"] = pbp_txt['plays']["end.team.id"].fillna(value=pbp_txt['plays']["start.team.id"]).apply(lambda x: int(x))
                pbp_txt['plays']['start.posteam.id'] = np.select(
                    [
                        (pbp_txt['plays']['type.text'].isin(kickoff_vec)) &
                        (pbp_txt['plays']['start.team.id'].astype(int) == pbp_txt['plays']['homeTeamId'].astype(int)),
                        (pbp_txt['plays']['type.text'].isin(kickoff_vec)) &
                        (pbp_txt['plays']['start.team.id'].astype(int) == pbp_txt['plays']['awayTeamId'].astype(int))
                    ],
                    [
                        pbp_txt['plays']['awayTeamId'].astype(int),
                        pbp_txt['plays']['homeTeamId'].astype(int)
                    ], default = pbp_txt['plays']['start.team.id'].astype(int)
                )
                pbp_txt['plays']['start.defteam.id'] = np.where(
                    pbp_txt['plays']['start.posteam.id'].astype(int) == pbp_txt['plays']['homeTeamId'].astype(int),
                    pbp_txt['plays']['awayTeamId'].astype(int), pbp_txt['plays']['homeTeamId'].astype(int)
                )
                pbp_txt['plays']["end.defteam.id"] = np.where(
                    pbp_txt['plays']["end.team.id"].astype(int) == pbp_txt['plays']['homeTeamId'].astype(int),
                    pbp_txt['plays']['awayTeamId'].astype(int), pbp_txt['plays']['homeTeamId'].astype(int)
                )
                pbp_txt['plays']['end.posteam.id'] = pbp_txt['plays']['end.team.id'].apply(lambda x: int(x))
                pbp_txt['plays']['end.defteam.id'] = pbp_txt['plays']['end.defteam.id'].apply(lambda x: int(x))
                pbp_txt['plays']['start.posteam.name'] = np.where(
                    pbp_txt['plays']['start.posteam.id'].astype(int) == pbp_txt['plays']['homeTeamId'].astype(int),
                    pbp_txt['plays']['homeTeamName'],pbp_txt['plays']['awayTeamName']
                )
                pbp_txt['plays']['start.defteam.name'] = np.where(
                    pbp_txt['plays']['start.posteam.id'].astype(int) == pbp_txt['plays']['homeTeamId'].astype(int),
                    pbp_txt['plays']['awayTeamName'], pbp_txt['plays']['homeTeamName']
                )
                pbp_txt['plays']['end.posteam.name'] = np.where(
                    pbp_txt['plays']['end.posteam.id'].astype(int) == pbp_txt['plays']['homeTeamId'].astype(int),
                    pbp_txt['plays']['homeTeamName'],pbp_txt['plays']['awayTeamName']
                )
                pbp_txt['plays']['end.defteam.name'] = np.where(
                    pbp_txt['plays']['end.posteam.id'].astype(int) == pbp_txt['plays']['homeTeamId'].astype(int),
                    pbp_txt['plays']['awayTeamName'], pbp_txt['plays']['homeTeamName']
                )
                pbp_txt['plays']['start.posteam_type'] = np.where(
                    pbp_txt['plays']["start.posteam.id"].astype(int) == pbp_txt['plays']['homeTeamId'].astype(int),
                    True, False
                )
                pbp_txt['plays']['end.posteam_type'] = np.where(
                    pbp_txt['plays']["end.posteam.id"].astype(int) == pbp_txt['plays']['homeTeamId'].astype(int),
                    True, False
                )
                pbp_txt['plays']['homeTimeoutCalled'] = np.where(
                    (pbp_txt['plays']['type.text']=='Timeout') &
                    ((pbp_txt['plays']['text'].str.lower().str.contains(str(homeTeamAbbrev),case=False))|
                    (pbp_txt['plays']['text'].str.lower().str.contains(str(homeTeamName), case=False))|
                    (pbp_txt['plays']['text'].str.lower().str.contains(str(homeTeamMascot), case=False))|
                    (pbp_txt['plays']['text'].str.lower().str.contains(str(homeTeamNameAlt), case=False))),
                    True, False
                )
                pbp_txt['plays']['awayTimeoutCalled'] = np.where(
                    (pbp_txt['plays']['type.text']=='Timeout') &
                    ((pbp_txt['plays']['text'].str.lower().str.contains(str(awayTeamAbbrev),case=False))|
                    (pbp_txt['plays']['text'].str.lower().str.contains(str(awayTeamName), case=False))|
                    (pbp_txt['plays']['text'].str.lower().str.contains(str(awayTeamMascot), case=False))|
                    (pbp_txt['plays']['text'].str.lower().str.contains(str(awayTeamNameAlt), case=False))),
                    True, False
                )
                pbp_txt['timeouts'][homeTeamId]["1"] = pbp_txt['plays'].loc[
                            (pbp_txt['plays']['homeTimeoutCalled'] == True) &
                            (pbp_txt['plays']['qtr'] <= 2)].reset_index()['id']
                pbp_txt['timeouts'][homeTeamId]["2"] = pbp_txt['plays'].loc[
                            (pbp_txt['plays']['homeTimeoutCalled'] == True) &
                            (pbp_txt['plays']['qtr'] > 2)
                            ].reset_index()['id']
                pbp_txt['timeouts'][awayTeamId]["1"] = pbp_txt['plays'].loc[
                            (pbp_txt['plays']['awayTimeoutCalled'] == True) &
                            (pbp_txt['plays']['qtr'] <= 2)
                            ].reset_index()['id']
                pbp_txt['timeouts'][awayTeamId]["2"] = pbp_txt['plays'].loc[
                            (pbp_txt['plays']['awayTimeoutCalled'] == True) &
                            (pbp_txt['plays']['qtr'] > 2)
                            ].reset_index()['id']

                pbp_txt['timeouts'][homeTeamId]["1"] = pbp_txt['timeouts'][homeTeamId]["1"].apply(lambda x: int(x))
                pbp_txt['timeouts'][homeTeamId]["2"] = pbp_txt['timeouts'][homeTeamId]["2"].apply(lambda x: int(x))
                pbp_txt['timeouts'][awayTeamId]["1"] = pbp_txt['timeouts'][awayTeamId]["1"].apply(lambda x: int(x))
                pbp_txt['timeouts'][awayTeamId]["2"] = pbp_txt['timeouts'][awayTeamId]["2"].apply(lambda x: int(x))
                pbp_txt['plays']['end.homeTeamTimeouts'] = 3 - pbp_txt['plays'].apply(
                    lambda x: ((pbp_txt['timeouts'][homeTeamId]["1"] <= x['id']) & (x['qtr'] <= 2))|
                            ((pbp_txt['timeouts'][homeTeamId]["2"] <= x['id']) & (x['qtr'] > 2)), axis = 1
                ).apply(lambda x: int(x.sum()), axis=1)
                pbp_txt['plays']['end.awayTeamTimeouts'] = 3 - pbp_txt['plays'].apply(
                    lambda x: ((pbp_txt['timeouts'][awayTeamId]["1"] <= x['id']) & (x['qtr'] <= 2))|
                            ((pbp_txt['timeouts'][awayTeamId]["2"] <= x['id']) & (x['qtr'] > 2)), axis = 1
                ).apply(lambda x: int(x.sum()), axis=1)
                pbp_txt['plays']['start.homeTeamTimeouts'] = pbp_txt['plays']['end.homeTeamTimeouts'].shift(1)
                pbp_txt['plays']['start.awayTeamTimeouts'] = pbp_txt['plays']['end.awayTeamTimeouts'].shift(1)
                pbp_txt['plays']['start.homeTeamTimeouts'] = np.where(
                    (pbp_txt['plays']['game_play_number'] == 1) |
                    ((pbp_txt['plays']['game_half'] == "2") & (pbp_txt['plays']['lag_game_half'] == "1")),
                    3, pbp_txt['plays']['start.homeTeamTimeouts']
                )
                pbp_txt['plays']['start.awayTeamTimeouts'] = np.where(
                    (pbp_txt['plays']['game_play_number'] == 1)|
                    ((pbp_txt['plays']['game_half'] == "2") & (pbp_txt['plays']['lag_game_half'] == "1")),
                    3, pbp_txt['plays']['start.awayTeamTimeouts']
                )
                pbp_txt['plays']['start.homeTeamTimeouts'] = pbp_txt['plays']['start.homeTeamTimeouts'].apply(lambda x: int(x))
                pbp_txt['plays']['start.awayTeamTimeouts'] = pbp_txt['plays']['start.awayTeamTimeouts'].apply(lambda x: int(x))
                pbp_txt['plays']['end.quarter_seconds_remaining'] = pbp_txt['plays']['start.quarter_seconds_remaining'].shift(1)
                pbp_txt['plays']['end.half_seconds_remaining'] = pbp_txt['plays']['start.half_seconds_remaining'].shift(1)
                pbp_txt['plays']['end.game_seconds_remaining'] = pbp_txt['plays']['start.game_seconds_remaining'].shift(1)
                pbp_txt['plays']['end.quarter_seconds_remaining'] = np.select(
                    [
                        (pbp_txt['plays']['game_play_number'] == 1)|
                        ((pbp_txt['plays']['qtr'] == 2) & (pbp_txt['plays']['lag_qtr'] == 1))|
                        ((pbp_txt['plays']['qtr'] == 3) & (pbp_txt['plays']['lag_qtr'] == 2))|
                        ((pbp_txt['plays']['qtr'] == 4) & (pbp_txt['plays']['lag_qtr'] == 3))
                    ],
                    [
                        900
                    ], default = pbp_txt['plays']['end.quarter_seconds_remaining']
                )
                pbp_txt['plays']['end.half_seconds_remaining'] = np.select(
                    [
                        (pbp_txt['plays']['game_play_number'] == 1)|
                        ((pbp_txt['plays']['game_half'] == "2") & (pbp_txt['plays']['lag_game_half'] == "1"))
                    ],
                    [
                        1800
                    ], default = pbp_txt['plays']['end.half_seconds_remaining']
                )
                pbp_txt['plays']['end.game_seconds_remaining'] = np.select(
                    [
                        (pbp_txt['plays']['game_play_number'] == 1),
                        ((pbp_txt['plays']['game_half'] == "2") & (pbp_txt['plays']['lag_game_half'] == "1"))
                    ],
                    [
                        3600,
                        1800
                    ], default = pbp_txt['plays']['end.game_seconds_remaining']
                )
                pbp_txt['plays']['start.posteamTimeouts'] = np.where(
                    pbp_txt['plays']['start.posteam.id'] == pbp_txt['plays']['homeTeamId'],
                    pbp_txt['plays']['start.homeTeamTimeouts'],
                    pbp_txt['plays']['start.awayTeamTimeouts']
                )
                pbp_txt['plays']['start.defteamTimeouts'] = np.where(
                    pbp_txt['plays']['start.defteam.id'] == pbp_txt['plays']['homeTeamId'],
                    pbp_txt['plays']['start.homeTeamTimeouts'],
                    pbp_txt['plays']['start.awayTeamTimeouts']
                )
                pbp_txt['plays']['end.posteamTimeouts'] = np.where(
                    pbp_txt['plays']['end.posteam.id'] == pbp_txt['plays']['homeTeamId'],
                    pbp_txt['plays']['end.homeTeamTimeouts'],
                    pbp_txt['plays']['end.awayTeamTimeouts']
                )
                pbp_txt['plays']['end.defteamTimeouts'] = np.where(
                    pbp_txt['plays']['end.defteam.id'] == pbp_txt['plays']['homeTeamId'],
                    pbp_txt['plays']['end.homeTeamTimeouts'],
                    pbp_txt['plays']['end.awayTeamTimeouts']
                )
                pbp_txt['firstHalfKickoffTeamId'] = np.where(
                    (pbp_txt['plays']['game_play_number'] == 1) &
                    (pbp_txt['plays']['type.text'].isin(kickoff_vec)) &
                    (pbp_txt['plays']['start.team.id'] == pbp_txt['plays']['homeTeamId']),
                    pbp_txt['plays']['homeTeamId'],
                    pbp_txt['plays']['awayTeamId']
                )
                pbp_txt['plays']['firstHalfKickoffTeamId'] = pbp_txt['firstHalfKickoffTeamId']
                pbp_txt['plays']['period'] = pbp_txt['plays']['qtr']
                pbp_txt['plays']['start.yard'] = np.where(
                    (pbp_txt['plays']['start.team.id'] == homeTeamId),
                    100 - pbp_txt['plays']['start.yardLine'],
                    pbp_txt['plays']['start.yardLine']
                )
                pbp_txt['plays']['start.yardsToEndzone'] = np.where(
                    pbp_txt['plays']['start.yardLine'].isna() == False,
                    pbp_txt['plays']['start.yardsToEndzone'],
                    pbp_txt['plays']['start.yard']
                )
                pbp_txt['plays']['start.yardsToEndzone'] = np.where(
                    pbp_txt['plays']['start.yardsToEndzone'] == 0,
                    pbp_txt['plays']['start.yard'],
                    pbp_txt['plays']['start.yardsToEndzone']
                )
                pbp_txt['plays']['end.yard'] = np.where(
                    (pbp_txt['plays']['end.team.id'] == homeTeamId),
                    100 - pbp_txt['plays']['end.yardLine'],
                    pbp_txt['plays']['end.yardLine']
                )
                pbp_txt['plays']['end.yard'] = np.where(
                    (pbp_txt['plays']['type.text'] == "Penalty") &
                    (pbp_txt['plays']["text"].str.contains("declined", case=False, flags=0, na=False, regex=True)),
                    pbp_txt['plays']['start.yard'],
                    pbp_txt['plays']['end.yard']
                )
                pbp_txt['plays']['end.yardsToEndzone'] = np.where(
                    pbp_txt['plays']['end.yardLine'].isna() == False,
                    pbp_txt['plays']['end.yardsToEndzone'],
                    pbp_txt['plays']['end.yard']
                )
                pbp_txt['plays']['end.yardsToEndzone'] = np.where(
                    (pbp_txt['plays']['type.text'] == "Penalty") &
                    (pbp_txt['plays']["text"].str.contains("declined", case=False, flags=0, na=False, regex=True)),
                    pbp_txt['plays']['start.yardsToEndzone'],
                    pbp_txt['plays']['end.yardsToEndzone']
                )
                pbp_txt['plays']['start.yardline_100'] = pbp_txt['plays']['start.yardsToEndzone']
                pbp_txt['plays']['end.yardline_100'] = pbp_txt['plays']['end.yardsToEndzone']
                pbp_txt['plays']['start.ydstogo'] = pbp_txt['plays']['start.distance']
                pbp_txt['plays']['end.ydstogo'] = pbp_txt['plays']['end.distance']
                pbp_txt['timeouts'][homeTeamId]["1"] = np.array(pbp_txt['timeouts'][homeTeamId]["1"]).tolist()
                pbp_txt['timeouts'][homeTeamId]["2"] = np.array(pbp_txt['timeouts'][homeTeamId]["2"]).tolist()
                pbp_txt['timeouts'][awayTeamId]["1"] = np.array(pbp_txt['timeouts'][awayTeamId]["1"]).tolist()
                pbp_txt['timeouts'][awayTeamId]["2"] = np.array(pbp_txt['timeouts'][awayTeamId]["2"]).tolist()
                if 'scoringType.displayName' in pbp_txt['plays'].keys():
                    pbp_txt['plays']['type.text'] = np.where(
                        pbp_txt['plays']['scoringType.displayName']=='Field Goal',
                        'Field Goal Good', pbp_txt['plays']['type.text']
                    )
                    pbp_txt['plays']['type.text'] = np.where(
                        pbp_txt['plays']['scoringType.displayName']=='Extra Point',
                        'Extra Point Good', pbp_txt['plays']['type.text']
                    )
                pbp_txt['plays']['playTypeOriginal'] = np.where(
                    pbp_txt['plays']['type.text'].isna() == False,
                    pbp_txt['plays']['type.text'], "Unknown"
                )
                pbp_txt['plays']['type.text'] = np.where(
                        pbp_txt['plays']['text'].str.lower().str.contains("extra point", case=False) &
                        pbp_txt['plays']['text'].str.lower().str.contains("no good", case=False),
                        'Extra Point Missed', pbp_txt['plays']['type.text']
                    )
                pbp_txt['plays']['type.text'] = np.where(
                    pbp_txt['plays']['text'].str.lower().str.contains("extra point", case=False) &
                    pbp_txt['plays']['text'].str.lower().str.contains("blocked", case=False),
                    'Extra Point Missed', pbp_txt['plays']['type.text']
                )
                pbp_txt['plays']['type.text'] = np.where(
                    pbp_txt['plays']['text'].str.lower().str.contains("field goal", case=False) &
                    pbp_txt['plays']['text'].str.lower().str.contains("blocked", case=False),
                    'Blocked Field Goal', pbp_txt['plays']['type.text']
                )
                pbp_txt['plays']['type.text'] = np.where(
                    pbp_txt['plays']['text'].str.lower().str.contains("field goal", case=False) &
                    pbp_txt['plays']['text'].str.lower().str.contains("no good", case=False),
                    'Field Goal Missed', pbp_txt['plays']['type.text']
                )
                del pbp_txt['plays']['clock.mm']
        else:
            pbp_txt['drives']={}
            pbp_txt['plays'] = pd.DataFrame()
            pbp_txt['timeouts'] = {}
            pbp_txt['timeouts'][homeTeamId] = {"1": [], "2": []}
            pbp_txt['timeouts'][awayTeamId] = {"1": [], "2": []}
        if 'scoringPlays' not in pbp_txt.keys():
            pbp_txt['scoringPlays'] = np.array([])
        if 'winprobability' not in pbp_txt.keys():
            pbp_txt['winprobability'] = np.array([])
        if 'standings' not in pbp_txt.keys():
            pbp_txt['standings'] = np.array([])
        if 'videos' not in pbp_txt.keys():
            pbp_txt['videos'] = np.array([])
        if 'broadcasts' not in pbp_txt.keys():
            pbp_txt['broadcasts'] = np.array([])
        pbp_txt['plays'] = pbp_txt['plays'].replace({np.nan: None})
        self.plays_json = pbp_txt['plays']
        pbp_json = {
            "gameId": self.gameId,
            "drives" : pbp_txt['drives'],
            "plays" : pbp_txt['plays'].to_dict(orient='records'),
            "scoringPlays" : np.array(pbp_txt['scoringPlays']).tolist(),
            "winprobability" : np.array(pbp_txt['winprobability']).tolist(),
            "boxscore" : pbp_txt['boxscore'],
            "header" : pbp_txt['header'],
            # "homeTeamSpread" : np.array(pbp_txt['homeTeamSpread']).tolist(),
            "broadcasts" : np.array(pbp_txt['broadcasts']).tolist(),
            "videos" : np.array(pbp_txt['videos']).tolist(),
            "playByPlaySource": pbp_txt['playByPlaySource'],
            "standings" : pbp_txt['standings'],
            "timeouts" : pbp_txt['timeouts'],
            "pickcenter" : np.array(pbp_txt['pickcenter']).tolist(),
            "againstTheSpread" : np.array(pbp_txt['againstTheSpread']).tolist(),
            "odds" : np.array(pbp_txt['odds']).tolist(),
            "predictor" : pbp_txt['predictor'],
            "espnWP" : np.array(pbp_txt['espnWP']).tolist(),
            "gameInfo" : np.array(pbp_txt['gameInfo']).tolist(),
            "season" : np.array(pbp_txt['season']).tolist()
        }
        return pbp_json

    def cfb_pbp_disk(self):
        with open(os.path.join(self.path_to_json, "{}.json".format(self.gameId))) as json_file:
            json_text = json.load(json_file)
            self.plays_json = pd.json_normalize(json_text,'plays')
            self.plays_json['week'] = json_text['header']['week']
        return json_text

    def setup_penalty_data(self, play_df):
        """
        Creates the following columns in play_df:
            * Penalty flag
            * Penalty declined
            * Penalty no play
            * Penalty off-set
            * Penalty 1st down conversion
            * Penalty in text
            * Yds Penalty
        """
            ##-- 'Penalty' in play text ----
            #-- T/F flag conditions penalty_flag
        play_df['penalty_flag'] = False
        play_df.loc[(play_df['type.text'] == "Penalty"), 'penalty_flag'] = True
        play_df.loc[play_df["text"].str.contains("penalty", case=False, flags=0, na=False, regex=True), 'penalty_flag'] = True

            #-- T/F flag conditions penalty_declined
        play_df['penalty_declined'] = False
        play_df.loc[(play_df['type.text'] == "Penalty") &
                    (play_df["text"].str.contains("declined", case=False, flags=0, na=False, regex=True)), 'penalty_declined'] = True
        play_df.loc[(play_df["text"].str.contains("penalty", case=False, flags=0, na=False, regex=True)) &
                    (play_df["text"].str.contains("declined", case=False, flags=0, na=False, regex=True)), 'penalty_declined'] = True

            #-- T/F flag conditions penalty_no_play
        play_df['penalty_no_play'] = False
        play_df.loc[(play_df['type.text'] == "Penalty") &
                    (play_df["text"].str.contains("no play", case=False, flags=0, na=False, regex=True)), 'penalty_no_play'] = True
        play_df.loc[(play_df["text"].str.contains("penalty", case=False, flags=0, na=False, regex=True)) &
                    (play_df["text"].str.contains("no play", case=False, flags=0, na=False, regex=True)), 'penalty_no_play'] = True

            #-- T/F flag conditions penalty_offset
        play_df['penalty_offset'] = False
        play_df.loc[(play_df['type.text'] == "Penalty") &
                    (play_df["text"].str.contains(r"off-setting", case=False, flags=0, na=False, regex=True)), 'penalty_offset'] = True
        play_df.loc[(play_df["text"].str.contains("penalty", case=False, flags=0, na=False, regex=True)) &
                    (play_df["text"].str.contains(r"off-setting", case=False, flags=0, na=False, regex=True)), 'penalty_offset'] = True

            #-- T/F flag conditions penalty_1st_conv
        play_df['penalty_1st_conv'] = False
        play_df.loc[(play_df['type.text'] == "Penalty") &
                    (play_df["text"].str.contains("1st down", case=False, flags=0, na=False, regex=True)), 'penalty_1st_conv'] = True
        play_df.loc[(play_df["text"].str.contains("penalty", case=False, flags=0, na=False, regex=True)) &
                    (play_df["text"].str.contains("1st down", case=False, flags=0, na=False, regex=True)), 'penalty_1st_conv'] = True

            #-- T/F flag for penalty text but not penalty play type --
        play_df['penalty_in_text'] = False
        play_df.loc[(play_df["text"].str.contains("penalty", case=False, flags=0, na=False, regex=True)) &
                    (~(play_df['type.text'] == "Penalty")) &
                    (~play_df["text"].str.contains("declined", case=False, flags=0, na=False, regex=True)) &
                    (~play_df["text"].str.contains(r"off-setting", case=False, flags=0, na=False, regex=True)) &
                    (~play_df["text"].str.contains("no play", case=False, flags=0, na=False, regex=True)), 'penalty_in_text'] = True

        play_df["penalty_detail"] = np.select(
            [
                (play_df.penalty_offset == 1),
                (play_df.penalty_declined == 1),
                play_df.text.str.contains(" roughing passer ", case=False, regex=True),
                play_df.text.str.contains(" offensive holding ", case=False, regex=True),
                play_df.text.str.contains(" pass interference", case=False, regex=True),
                play_df.text.str.contains(" encroachment", case=False, regex=True),
                play_df.text.str.contains(" defensive pass interference ", case=False, regex=True),
                play_df.text.str.contains(" offensive pass interference ", case=False, regex=True),
                play_df.text.str.contains(" illegal procedure ", case=False, regex=True),
                play_df.text.str.contains(" defensive holding ", case=False, regex=True),
                play_df.text.str.contains(" holding ", case=False, regex=True),
                play_df.text.str.contains(" offensive offside | offside offense", case=False, regex=True),
                play_df.text.str.contains(" defensive offside | offside defense", case=False, regex=True),
                play_df.text.str.contains(" offside ", case=False, regex=True),
                play_df.text.str.contains(" illegal fair catch signal ", case=False, regex=True),
                play_df.text.str.contains(" illegal batting ", case=False, regex=True),
                play_df.text.str.contains(" neutral zone infraction ", case=False, regex=True),
                play_df.text.str.contains(" ineligible downfield ", case=False, regex=True),
                play_df.text.str.contains(" illegal use of hands ", case=False, regex=True),
                play_df.text.str.contains(" kickoff out of bounds | kickoff out-of-bounds ", case=False, regex=True),
                play_df.text.str.contains(" 12 men on the field ", case=False, regex=True),
                play_df.text.str.contains(" illegal block ", case=False, regex=True),
                play_df.text.str.contains(" personal foul ", case=False, regex=True),
                play_df.text.str.contains(" false start ", case=False, regex=True),
                play_df.text.str.contains(" substitution infraction ", case=False, regex=True),
                play_df.text.str.contains(" illegal formation ", case=False, regex=True),
                play_df.text.str.contains(" illegal touching ", case=False, regex=True),
                play_df.text.str.contains(" sideline interference ", case=False, regex=True),
                play_df.text.str.contains(" clipping ", case=False, regex=True),
                play_df.text.str.contains(" sideline infraction ", case=False, regex=True),
                play_df.text.str.contains(" crackback ", case=False, regex=True),
                play_df.text.str.contains(" illegal snap ", case=False, regex=True),
                play_df.text.str.contains(" illegal helmet contact ", case=False, regex=True),
                play_df.text.str.contains(" roughing holder ", case=False, regex=True),
                play_df.text.str.contains(" horse collar tackle ", case=False, regex=True),
                play_df.text.str.contains(" illegal participation ", case=False, regex=True),
                play_df.text.str.contains(" tripping ", case=False, regex=True),
                play_df.text.str.contains(" illegal shift ", case=False, regex=True),
                play_df.text.str.contains(" illegal motion ", case=False, regex=True),
                play_df.text.str.contains(" roughing the kicker ", case=False, regex=True),
                play_df.text.str.contains(" delay of game ", case=False, regex=True),
                play_df.text.str.contains(" targeting ", case=False, regex=True),
                play_df.text.str.contains(" face mask ", case=False, regex=True),
                play_df.text.str.contains(" illegal forward pass ", case=False, regex=True),
                play_df.text.str.contains(" intentional grounding ", case=False, regex=True),
                play_df.text.str.contains(" illegal kicking ", case=False, regex=True),
                play_df.text.str.contains(" illegal conduct ", case=False, regex=True),
                play_df.text.str.contains(" kick catching interference ", case=False, regex=True),
                play_df.text.str.contains(" unnecessary roughness ", case=False, regex=True),
                play_df.text.str.contains("Penalty, UR"),
                play_df.text.str.contains(" unsportsmanlike conduct ", case=False, regex=True),
                play_df.text.str.contains(" running into kicker ", case=False, regex=True),
                play_df.text.str.contains(" failure to wear required equipment ", case=False, regex=True),
                play_df.text.str.contains(" player disqualification ", case=False, regex=True),
                (play_df.penalty_flag == True)
            ],
            [
                "Off-Setting",
                "Penalty Declined",
                "Roughing the Passer",
                "Offensive Holding",
                "Pass Interference",
                "Encroachment",
                "Defensive Pass Interference",
                "Offensive Pass Interference",
                "Illegal Procedure",
                "Defensive Holding",
                "Holding",
                "Offensive Offside",
                "Defensive Offside",
                "Offside",
                "Illegal Fair Catch Signal",
                "Illegal Batting",
                "Neutral Zone Infraction",
                "Ineligible Man Down-Field",
                "Illegal Use of Hands",
                "Kickoff Out-of-Bounds",
                "12 Men on the Field",
                "Illegal Block",
                "Personal Foul",
                "False Start",
                "Substitution Infraction",
                "Illegal Formation",
                "Illegal Touching",
                "Sideline Interference",
                "Clipping",
                "Sideline Infraction",
                "Crackback",
                "Illegal Snap",
                "Illegal Helmet contact",
                "Roughing the Holder",
                "Horse-Collar Tackle",
                "Illegal Participation",
                "Tripping",
                "Illegal Shift",
                "Illegal Motion",
                "Roughing the Kicker",
                "Delay of Game",
                "Targeting",
                "Face Mask",
                "Illegal Forward Pass",
                "Intentional Grounding",
                "Illegal Kicking",
                "Illegal Conduct",
                "Kick Catch Interference",
                "Unnecessary Roughness",
                "Unnecessary Roughness",
                "Unsportsmanlike Conduct",
                "Running Into Kicker",
                "Failure to Wear Required Equipment",
                "Player Disqualification",
                "Missing"
            ], default = None)

        play_df['penalty_text'] = np.where(
            (play_df.penalty_flag == True),
            play_df.text.str.extract(r"Penalty(.+)", flags=re.IGNORECASE)[0],
            None
        )

        play_df['yds_penalty'] = np.where(
            (play_df.penalty_flag == True),
            play_df.penalty_text.str.extract("(.{0,3})yards|yds|yd to the ", flags=re.IGNORECASE)[0],
            None
        )
        play_df['yds_penalty'] = play_df['yds_penalty'].str.replace( " yards to the | yds to the | yd to the ", "", regex = True)
        play_df['yds_penalty'] = np.where(
            (play_df.penalty_flag == True) & (play_df.text.str.contains(r"ards\)", case=False, regex=True)) & (play_df.yds_penalty.isna()),
            play_df.text.str.extract(r"(.{0,4})yards\)|Yards\)|yds\)|Yds\)",flags=re.IGNORECASE)[0],
            play_df.yds_penalty
        )
        play_df['yds_penalty'] = play_df.yds_penalty.str.replace( "yards\\)|Yards\\)|yds\\)|Yds\\)", "", regex = True).str.replace( "\\(", "", regex = True)
        return play_df

    def add_downs_data(self, play_df):
        """
        Creates the following columns in play_df:
            * id, drive_id, game_id
            * down, ydstogo (distance), game_half, period
        """
        play_df = self.plays_json
        play_df = play_df.assign(id =  lambda play_df: play_df['id'].astype(float))
        play_df = play_df.assign(play_id =  lambda play_df: play_df['id'].astype(float))
        play_df = play_df[play_df['type.text'].str.contains("end of| coin toss |end period",case=False, regex=True) == False]

        play_df = play_df.assign(period = lambda play_df: play_df['period'].astype(int))
        play_df = play_df.assign(qtr = lambda play_df: play_df['period'].astype(int))
        play_df.loc[(play_df.qtr <= 2),'half'] = 1
        play_df.loc[(play_df.qtr > 2),'half'] = 2
        play_df.loc[(play_df.qtr <= 2),'game_half'] = 1
        play_df.loc[(play_df.qtr > 2),'game_half'] = 2
        play_df = play_df.assign(lead_game_half= play_df.game_half.shift(-1))
        play_df = play_df.assign(lag_scoringPlay = play_df.scoringPlay.shift(1))
        play_df.loc[play_df.lead_game_half.isna() == True, 'lead_game_half'] = 2
        play_df.loc[(play_df.game_half != play_df.lead_game_half),'end_of_half'] = True


        play_df.loc[(play_df["start.down"] == 1),'down_1'] = True
        play_df.loc[(play_df["start.down"] == 2),'down_2'] = True
        play_df.loc[(play_df["start.down"] == 3),'down_3'] = True
        play_df.loc[(play_df["start.down"] == 4),'down_4'] = True

        play_df.loc[(play_df["end.down"] == 1),'down_1_end'] = True
        play_df.loc[(play_df["end.down"] == 2),'down_2_end'] = True
        play_df.loc[(play_df["end.down"] == 3),'down_3_end'] = True
        play_df.loc[(play_df["end.down"] == 4),'down_4_end'] = True
        return play_df

    def add_play_type_flags(self, play_df):
        """
        Creates the following columns in play_df:
            * Flags for fumbles, scores, kickoffs, punts, field goals
            * Rush, Pass, Sacks
        """
        #--- Touchdown, Fumble, Special Teams flags -----------------
        play_df.loc[
            (play_df["type.text"].isin(scores_vec)),
            "scoring_play"] = True
        play_df.loc[
            (play_df.text.str.contains(r"touchdown|for a TD", case=False, flags=0, na=False, regex=True)),
            "td_play"] = True

        play_df.loc[
            (play_df["type.text"].str.contains("touchdown", case=False, flags=0, na=False, regex=True)),
            "touchdown"] = True
        play_df.loc[
            play_df["text"].str.contains("safety", case=False, flags=0, na=False, regex=True),
            "safety"] = True

        #--- Fumbles----
        play_df.loc[
            play_df["text"].str.contains("fumble", case=False, flags=0, na=False, regex=True),
            "fumble"] = True

        play_df.loc[
            play_df["text"].str.contains("forced by", case=False, flags=0, na=False, regex=True),
            "fumble_forced"] = True
        play_df.loc[
            (play_df["text"].str.contains("fumble", case=False, flags=0, na=False, regex=True)) &
            (~play_df["text"].str.contains("forced by", case=False, flags=0, na=False, regex=True)),
            "fumble_not_forced"] = False
        #--- Kicks----
        play_df.loc[
            play_df["type.text"].isin(kickoff_vec),
            "kickoff_play"] = True

        play_df.loc[
            (play_df["text"].str.contains("touchback", case=False, flags=0, na=False, regex=True)) &
            (play_df.kickoff_play == True),
            "kickoff_tb"] = True

        play_df.loc[
            (play_df["text"].str.contains(r"on-side|onside|on side", case=False, flags=0, na=False, regex=True)) &
            (play_df.kickoff_play == True),
            "kickoff_onside"] = True

        play_df.loc[
            (play_df["text"].str.contains(r"out-of-bounds|out of bounds", case=False, flags=0, na=False, regex=True)) &
            (play_df.kickoff_play == True),
            "kickoff_oob"] = True

        play_df.loc[
            (play_df["text"].str.contains(r"fair catch|fair caught", case=False, flags=0, na=False, regex=True)) &
            (play_df.kickoff_play == True),
            "kickoff_fair_catch"] =  True

        play_df.loc[
            (play_df["text"].str.contains("downed", case=False, flags=0, na=False, regex=True)) &
            (play_df.kickoff_play == True),
            "kickoff_downed"] = True

        play_df.loc[
            play_df["text"].str.contains(r"kick|kickoff", case=False, flags=0, na=False, regex=True),
            "kick_play"] = True

        play_df.loc[
            (~play_df["type.text"].isin(['Blocked Punt','Penalty'])) &
             (play_df["text"].str.contains("kickoff", case=False, flags=0, na=False, regex=True)) &
              (play_df.safety == True),
              "kickoff_safety"] = True

        #--- Punts----
        play_df.loc[
            play_df["type.text"].isin(punt_vec),
            "punt"] =  True

        play_df.loc[
            play_df["text"].str.contains("punt", case=False, flags=0, na=False, regex=True), 
            "punt_play"] = True

        play_df.loc[
            (play_df["text"].str.contains("touchback", case=False, flags=0, na=False, regex=True)) &
            (play_df.punt == True),
            "punt_tb"] = True

        play_df.loc[
            (play_df["text"].str.contains(r"out-of-bounds|out of bounds", case=False, flags=0, na=False, regex=True)) &
            (play_df.punt == True),
            "punt_oob"] = True

        play_df.loc[
            (play_df["text"].str.contains(r"fair catch|fair caught", case=False, flags=0, na=False, regex=True)) &
            (play_df.punt == True),
            "punt_fair_catch"] = True

        play_df.loc[
            (play_df["text"].str.contains("downed", case=False, flags=0, na=False, regex=True)) &
            (play_df.punt == True),
            "punt_downed"] = True

        play_df.loc[
            (play_df["type.text"].isin(['Blocked Punt','Punt'])) &
            (play_df["text"].str.contains("punt", case=False, flags=0, na=False, regex=True)) &
            (play_df.safety == True),
            "punt_safety"] = True

        play_df.loc[
            (play_df["type.text"].isin(['Penalty'])) &
            (play_df.safety == True),
            "penalty_safety"] = True

        play_df.loc[
            (play_df["text"].str.contains("blocked", case=False, flags=0, na=False, regex=True)) &
            (play_df.punt == True),
            "punt_blocked"] = True
        return play_df

    def add_rush_pass_flags(self, play_df):
        """
        Creates the following columns in play_df:
            * Rush, Pass, Sacks
        """

        #--- Pass/Rush----
        play_df.loc[((play_df["type.text"] == "Rush") | (play_df["type.text"] == "Rushing Touchdown") | (play_df["type.text"].isin(["Safety","Fumble Recovery (Opponent)","Fumble Recovery (Opponent) Touchdown", "Fumble Recovery (Own)", "Fumble Recovery (Own) Touchdown", "Fumble Return Touchdown"]) & play_df["text"].str.contains("run for"))), 'rush'] = True

        play_df.loc[(
                (play_df["type.text"].isin(["Pass Reception", "Pass Completion","Passing Touchdown","Sack","Pass","Interception","Pass Interception Return", "Interception Return Touchdown","Pass Incompletion","Sack Touchdown","Interception Return"])) |
                ((play_df["type.text"] == "Safety") & (play_df["text"].str.contains("sacked", case=False, flags=0, na=False, regex=True))) |
                ((play_df["type.text"] == "Safety") & (play_df["text"].str.contains("pass complete", case=False, flags=0, na=False, regex=True))) |
                ((play_df["type.text"] == "Fumble Recovery (Own)") & (play_df["text"].str.contains(r"pass complete|pass incomplete|pass intercepted", case=False, flags=0, na=False, regex=True))) |
                ((play_df["type.text"] == "Fumble Recovery (Own)") & (play_df["text"].str.contains("sacked", case=False, flags=0, na=False, regex=True))) |
                ((play_df["type.text"] == "Fumble Recovery (Own) Touchdown") & (play_df["text"].str.contains(r"pass complete|pass incomplete|pass intercepted", case=False, flags=0, na=False, regex=True))) |
                ((play_df["type.text"] == "Fumble Recovery (Own) Touchdown") & (play_df["text"].str.contains("sacked", case=False, flags=0, na=False, regex=True))) |
                ((play_df["type.text"] == "Fumble Recovery (Opponent)") & (play_df["text"].str.contains(r"pass complete|pass incomplete|pass intercepted", case=False, flags=0, na=False, regex=True))) |
                ((play_df["type.text"] == "Fumble Recovery (Opponent)") & (play_df["text"].str.contains("sacked", case=False, flags=0, na=False, regex=True))) |
                ((play_df["type.text"] == "Fumble Recovery (Opponent) Touchdown") & (play_df["text"].str.contains(r"pass complete|pass incomplete", case=False, flags=0, na=False, regex=True))) |
                ((play_df["type.text"] == "Fumble Return Touchdown") & (play_df["text"].str.contains(r"pass complete|pass incomplete", case=False, flags=0, na=False, regex=True))) |
                ((play_df["type.text"] == "Fumble Return Touchdown") & (play_df["text"].str.contains("sacked", case=False, flags=0, na=False, regex=True)))
                ), 'pass'] = True

        # #--- Sacks----
        play_df['sack_vec'] = np.select(
            [
                (
                    (play_df["type.text"].isin(["Sack", "Sack Touchdown"])) |
                    ((play_df["type.text"].isin(["Fumble Recovery (Own)", "Fumble Recovery (Own) Touchdown", "Fumble Recovery (Opponent)", "Fumble Recovery (Opponent) Touchdown", "Fumble Return Touchdown"]) &
                    (play_df["pass"] == True) &
                    (play_df["text"].str.contains("sacked", case=False, flags=0, na=False, regex=True))
                    ))
                )
            ],
            [True], default = False
        )

        return play_df

    def add_team_score_variables(self, play_df):
        """
        Creates the following columns in play_df:
            * Team Score variables
            * Fix play types
            * Fix change of poss variables
        """
        # #-------------------------
        play_df['posteam'] = np.select(
            [
                True
            ],
            [
                play_df['start.posteam.id']
            ], default = None
        )
        play_df['defteam'] = np.select(
            [
                True
            ],
            [
                play_df['start.defteam.id']
            ], default = None
        )
        play_df['posteam_type'] = np.select(
            [
                (play_df.posteam == play_df["homeTeamId"])
            ],
            [True], default = False
        )
        #--- Team Score variables ------
        play_df['lag_homeScore'] = np.select(
            [
                True
            ],
            [
                play_df['homeScore'].shift(1)
            ], default = None
        )
        play_df['lag_awayScore'] = np.select(
            [
                True
            ],
            [
                play_df['awayScore'].shift(1)
            ], default = None
        )
        play_df['lag_HA_score_differential'] = np.select(
            [
                True
            ],
            [
                play_df['lag_homeScore'] - play_df['lag_awayScore']
            ], default = None
        )
        play_df['HA_score_differential'] = np.select(
            [
                True
            ],
            [
                play_df['homeScore'] - play_df['awayScore']
            ], default = None
        )
        play_df['net_HA_score_pts'] = np.select(
            [
                True
            ],
            [
                play_df['HA_score_differential'] - play_df['lag_HA_score_differential']
            ], default = None
        )
        play_df['H_score_differential'] = np.select(
            [
                True
            ],
            [
                play_df['homeScore'] - play_df['lag_homeScore']
            ], default = None
        )
        play_df['A_score_differential'] = np.select(
            [
                True
            ],
            [
                play_df['awayScore'] - play_df['lag_awayScore']
            ], default = None
        )
        play_df['homeScore'] = np.select(
            [
                (play_df.scoringPlay == False) & (play_df['game_play_number'] != 1) &
                (play_df['H_score_differential'] >= 9),
                (play_df.scoringPlay == False) & (play_df['game_play_number'] != 1) &
                (play_df['H_score_differential'] < 9) & (play_df['H_score_differential'] > 1),
                (play_df.scoringPlay == False) & (play_df['game_play_number'] != 1) &
                (play_df['H_score_differential'] >= -9) & (play_df['H_score_differential'] < -1)
            ],
            [
                play_df['lag_homeScore'],
                play_df['lag_homeScore'],
                play_df['homeScore']
            ], default = play_df['homeScore']
        )
        play_df['awayScore'] =  np.select(
            [
                (play_df.scoringPlay == False) & (play_df['game_play_number'] != 1) &
                (play_df['A_score_differential'] >= 9),
                (play_df.scoringPlay == False) & (play_df['game_play_number'] != 1) &
                (play_df['A_score_differential'] < 9) & (play_df['A_score_differential'] > 1),
                (play_df.scoringPlay == False) & (play_df['game_play_number'] != 1) &
                (play_df['A_score_differential'] >= -9) & (play_df['A_score_differential'] < -1)],
            [
                play_df['lag_awayScore'],
                play_df['lag_awayScore'],
                play_df['awayScore']
            ], default = play_df['awayScore']
        )
        play_df.drop(['lag_homeScore','lag_awayScore'], axis=1, inplace=True)
        play_df['lag_homeScore'] = np.select(
            [
                True
            ],
            [
                play_df['homeScore'].shift(1)
            ], default = None
        )
        play_df['lag_awayScore'] = np.select(
            [
                True
            ],
            [
                play_df['awayScore'].shift(1)
            ], default = None
        )
        play_df['start.homeScore'] = np.select(
            [
                play_df["game_play_number"] == 1
            ],
            [0], default = play_df['lag_homeScore']
        )
        play_df['start.awayScore'] = np.select(
            [
                play_df["game_play_number"] == 1
            ],
            [0], default = play_df['lag_awayScore']
        )
        play_df['end.homeScore'] = np.select(
            [
                True
            ],
            [
                play_df['homeScore']
            ], default = None
        )
        play_df['end.awayScore'] = np.select(
            [
                True
            ],
            [
                play_df['awayScore']
            ], default = None
        )
        play_df['posteam_score'] = np.select(
            [
                play_df.posteam == play_df["homeTeamId"]
            ],
            [
                play_df.homeScore
            ], default = play_df.awayScore
        )
        play_df['defteam_score'] = np.select(
            [
                play_df.posteam == play_df["homeTeamId"]
            ],
            [
                play_df.awayScore
            ], default = play_df.homeScore
        )
        play_df['start.posteam_score'] = np.select(
            [
                play_df['start.posteam.id'] == play_df["homeTeamId"]
            ],
            [
                play_df['start.homeScore']
            ], default = play_df['start.awayScore']
        )
        play_df['start.defteam_score'] = np.select(
            [
                play_df['start.posteam.id'] == play_df["homeTeamId"]
            ],
            [
                play_df['start.awayScore']
            ], default = play_df['start.homeScore']
        )
        play_df['start.posteam_score_differential'] =  np.select(
            [
                True
            ],
            [
                play_df['start.posteam_score'] - play_df['start.defteam_score']
            ], default = None
        )
        play_df['end.posteam_score'] = np.select(
            [
                play_df['end.posteam.id'] == play_df["homeTeamId"]
            ],
            [
                play_df['end.homeScore']
            ], default = play_df['end.awayScore']
        )
        play_df['end.defteam_score'] = np.select(
            [
                play_df['end.posteam.id'] == play_df["homeTeamId"]
            ],
            [
                play_df['end.awayScore']
            ], default = play_df['end.homeScore']
        )
        play_df['end.posteam_score_differential'] = np.select(
            [
                True
            ],
            [
                play_df['end.posteam_score'] - play_df['end.defteam_score']
            ], default = None
        )
        play_df['lag_posteam'] = np.select(
            [
                True
            ],
            [
                play_df['posteam'].shift(1)
            ], default = None
        )
        play_df.loc[play_df.lag_posteam.isna() == True, 'lag_posteam'] = play_df.posteam
        play_df['lead_posteam'] = np.select(
            [
                True
            ],
            [
                play_df['posteam'].shift(-1)
            ], default = None
        )
        play_df['lead_posteam2'] = np.select(
            [
                True
            ],
            [
                play_df['posteam'].shift(-2)
            ], default = None
        )
        play_df['posteam_score_differential'] = np.select(
            [
                True
            ],
            [
                play_df.posteam_score - play_df.defteam_score
            ], default = None
        )
        play_df['lag_posteam_score_differential'] = np.select(
            [
                True
            ],
            [
                play_df['posteam_score_differential'].shift(1)
            ], default = None
        )
        play_df.loc[play_df.posteam_score_differential.isna() == True, 'lag_posteam_score_differential'] = 0
        play_df['posteam_score_pts'] = np.select(
            [
                play_df.lag_posteam == play_df.posteam
            ],
            [
                play_df.posteam_score_differential - play_df.lag_posteam_score_differential
            ], default = play_df.posteam_score_differential + play_df.lag_posteam_score_differential
        )
        play_df['posteam_score_differential'] = np.select(
            [
                (play_df.kickoff_play == False) & (play_df.lag_posteam == play_df.posteam)
            ],
            [
                play_df.lag_posteam_score_differential
            ], default = -1 * play_df.lag_posteam_score_differential
        )
        #--- Timeouts ------
        play_df.loc[play_df.posteam_score_differential.isna() == True, 'posteam_score_differential'] = play_df.posteam_score_differential
        play_df['start.posteam_receives_2H_kickoff'] = np.select(
            [
                True
            ],
            [
                (play_df["start.posteam.id"] == play_df.firstHalfKickoffTeamId)
            ], default = False
        )
        play_df['end.posteam_receives_2H_kickoff'] = np.select(
            [
                True
            ],
            [
                (play_df["end.posteam.id"] == play_df.firstHalfKickoffTeamId)
            ], default = False
        )
        play_df['change_of_poss'] = np.select(
            [
                play_df["start.posteam.id"] == play_df["end.posteam.id"]
            ],
            [
                False
            ], default = True
        )
        play_df['change_of_poss'] = np.select(
            [
                play_df['change_of_poss'].isna()
            ],
            [
                0
            ], default = play_df['change_of_poss']
        )
        return play_df

    def add_new_play_types(self, play_df):
        play_df = self.plays_json
    #--------------------------------------------------
        ## Fix Strip-Sacks to Fumbles----
        play_df['type.text'] = np.select(
            [
                (play_df['fumble'] == True) & (play_df["pass"] == True) &
                (play_df['change_of_poss'] == 1) & (play_df['td_play'] == False) &
                (play_df["start.down"] != 4) & ~(play_df['type.text'].isin(defense_score_vec))
            ],
            [
                "Fumble Recovery (Opponent)"
            ], default = play_df['type.text']
        )
        play_df['type.text'] = np.select(
            [
                (play_df['fumble'] == True) & (play_df["pass"] == True) &
                (play_df['change_of_poss'] == 1) & (play_df['td_play'] == True)
            ],
            [
                "Fumble Recovery (Opponent) Touchdown"
            ], default = play_df['type.text']
        )
        ## Fix rushes with fumbles and a change of possession to fumbles----
        play_df['type.text'] = np.select(
            [
                (play_df['fumble'] == True) & (play_df["rush"] == True) &
                (play_df['change_of_poss'] == 1) & (play_df['td_play'] == False) &
                (play_df["start.down"] != 4) & ~(play_df['type.text'].isin(defense_score_vec))
            ],
            [
                "Fumble Recovery (Opponent)"
            ], default = play_df['type.text']
        )
        play_df['type.text'] = np.select(
            [
                (play_df['fumble'] == True) & (play_df["rush"] == True) &
                (play_df['change_of_poss'] == 1) & (play_df['td_play'] == True)
            ],
            [
                "Fumble Recovery (Opponent) Touchdown"
            ], default = play_df['type.text']
        )
        ## Portion of touchdown check for plays where touchdown is not listed in the play_type--
        play_df["td_check"] = np.select(
            [
                play_df["text"].str.contains("Touchdown", case=False, flags=0, na=False, regex=True)
            ],
            [
                True
            ], default = False
        )

        #-- Fix kickoff fumble return TDs ----
        play_df['type.text'] = np.select(
            [
                (play_df.kickoff_play == True) & (play_df.change_of_poss == 1) &
                (play_df.td_play == True) & (play_df.td_check == True)
            ],
            [
                "Kickoff Return Touchdown"
            ], default = play_df['type.text']
        )
        #-- Fix punt return TDs ----
        play_df['type.text'] = np.select(
            [
                (play_df.punt_play == True) & (play_df.td_play == True) &
                (play_df.td_check == True),
            ],
            [
                "Punt Return Touchdown"
            ], default = play_df['type.text']
        )
        #-- Fix kick return TDs----
        play_df['type.text'] = np.select(
            [
                (play_df.kickoff_play == True) & (play_df.fumble == False) &
                (play_df.td_play == True) & (play_df.td_check == True)
            ],
            [
                "Kickoff Return Touchdown"
            ], default = play_df['type.text']
        )
        #-- Fix rush/pass tds that aren't explicit----
        play_df['type.text'] = np.select(
            [
                (play_df.td_play == True) &
                (play_df.rush == True) &
                (play_df.fumble == False) &
                (play_df.td_check == True)
            ],
            [
                "Rushing Touchdown"
            ], default = play_df['type.text']
        )
        play_df['type.text'] = np.select(
            [
                (play_df.td_play == True) & (play_df["pass"] == True) &
                (play_df.fumble == False) & (play_df.td_check == True) &
                ~(play_df['type.text'].isin(int_vec))
            ],
            [
                "Passing Touchdown" 
            ], default = play_df['type.text']
        )
        play_df['type.text'] = np.select(
            [
                (play_df["pass"] == True) &
                (play_df['type.text'].isin(["Pass Reception", "Pass Completion", "Pass"])) &
                (play_df.statYardage == play_df["start.yardline_100"]) &
                (play_df.fumble == False) & ~(play_df['type.text'].isin(int_vec))
            ],
            [
                "Passing Touchdown"
            ], default = play_df['type.text']
        )
        play_df['type.text'] = np.select(
            [
                (play_df['type.text'].isin(["Blocked Field Goal"])) &
                (play_df['text'].str.contains("for a TD", case=False, flags=0, na=False, regex=True))
            ],
            [
                "Blocked Field Goal Touchdown"
            ], default = play_df['type.text']
        )
        #-- Fix duplicated TD play_type labels----
        play_df['type.text'] = np.select(
            [
                play_df['type.text'] == "Punt Touchdown Touchdown"
            ],
            [
                "Punt Touchdown"
            ], default = play_df['type.text']
        )
        play_df['type.text'] = np.select(
            [
                play_df['type.text'] == "Fumble Return Touchdown Touchdown"
            ],
            [
                 "Fumble Return Touchdown"
            ], default = play_df['type.text']
        )
        play_df['type.text'] = np.select(
            [
                play_df['type.text'] == "Rushing Touchdown Touchdown"
            ],
            [
                "Rushing Touchdown"
            ], default = play_df['type.text']
        )
        play_df['type.text'] = np.select(
            [
                play_df['type.text'] == "Uncategorized Touchdown Touchdown"
            ],
            [
                "Uncategorized Touchdown"
            ], default = play_df['type.text']
        )
        #-- Fix Pass Interception Return TD play_type labels----
        play_df['type.text'] = np.select(
            [
                play_df["text"].str.contains("pass intercepted for a TD", case=False, flags=0, na=False, regex=True)
            ],
            [
                "Interception Return Touchdown"
            ], default = play_df['type.text']
        )
        #-- Fix Sack/Fumbles Touchdown play_type labels----
        play_df['type.text'] = np.select(
            [
                (play_df["text"].str.contains("sacked", case=False, flags=0, na=False, regex=True)) &
                (play_df["text"].str.contains("fumbled", case=False, flags=0, na=False, regex=True)) &
                (play_df["text"].str.contains("TD", case=False, flags=0, na=False, regex=True))
            ],
            [
                "Fumble Recovery (Opponent) Touchdown"
            ], default = play_df['type.text']
        )
        #-- Fix generic pass plays ----
        ##-- first one looks for complete pass
        play_df['type.text'] = np.select(
            [
                (play_df['type.text'] == "Pass") &
                (play_df.text.str.contains("pass complete", case=False, flags=0, na=False, regex=True))
            ],
            [
                "Pass Completion"
            ], default = play_df['type.text']
        )
        ##-- second one looks for incomplete pass
        play_df['type.text'] = np.select(
            [
                (play_df['type.text'] == "Pass") &
                (play_df.text.str.contains("pass incomplete", case=False, flags=0, na=False, regex=True))
            ],
            [
                "Pass Incompletion"
            ], default = play_df['type.text']
        )
        ##-- third one looks for interceptions
        play_df['type.text'] = np.select(
            [
                (play_df['type.text'] == "Pass") &
                (play_df.text.str.contains("pass intercepted", case=False, flags=0, na=False, regex=True))
            ],
            [
                "Pass Interception"
            ], default = play_df['type.text']
        )
        ##-- fourth one looks for sacked
        play_df['type.text'] = np.select(
            [
                (play_df['type.text'] == "Pass") &
                (play_df.text.str.contains("sacked", case=False, flags=0, na=False, regex=True))
            ],
            [
                "Sack"
            ], default = play_df['type.text']
        )
        ##-- fifth one play type is Passing Touchdown, but its intercepted
        play_df['type.text'] = np.select(
            [
                (play_df['type.text'] == "Passing Touchdown") &
                (play_df.text.str.contains("pass intercepted for a TD", case=False, flags=0, na=False, regex=True)),
            ],
            [
                "Interception Return Touchdown"
            ], default = play_df['type.text']
        )
        play_df['type.text'] = np.select(
            [
                (play_df['type.text'] == "Passing Touchdown") &
                (play_df.text.str.contains("pass intercepted for a TD", case=False, flags=0, na=False, regex=True))
            ],
            [
                "Interception Return Touchdown"
            ], default = play_df['type.text']
        )
        #--- Moving non-Touchdown pass interceptions to one play_type: "Interception Return" -----
        play_df['type.text'] = np.select(
            [
                play_df['type.text'].isin(["Interception"])
            ],
            [
                "Interception Return"
            ], default = play_df['type.text']
        )
        play_df['type.text'] = np.select(
            [
                play_df['type.text'].isin(["Pass Interception"])
            ],
            [
                "Interception Return"
            ], default = play_df['type.text']
        )
        play_df['type.text'] = np.select(
            [
                play_df['type.text'].isin(["Pass Interception Return"])
            ],
            [
                "Interception Return"
            ], default = play_df['type.text']
        )

        #--- Moving Kickoff/Punt Touchdowns without fumbles to Kickoff/Punt Return Touchdown
        play_df['type.text'] =  np.select(
            [
                (play_df['type.text'] == "Kickoff Touchdown") &
                (play_df.fumble == False)
            ],
            [
                "Kickoff Return Touchdown"
            ], default = play_df['type.text']
        )

        play_df['type.text'] = np.select(
            [
                (play_df['type.text'].isin(["Kickoff", "Kickoff Return (Offense)"])) &
                (play_df.fumble == True) & (play_df.change_of_poss == 1)
            ],
            [
                "Kickoff Team Fumble Recovery"
            ], default = play_df['type.text']
        )

        play_df['type.text'] = np.select(
            [
                (play_df['type.text'] == "Punt Touchdown") &
                (play_df.fumble == False) & (play_df.change_of_poss == 1)
            ],
            [
                "Punt Return Touchdown"
            ], default = play_df['type.text']
        )
        play_df['type.text'] = np.select(
            [
                (play_df['type.text'] == "Punt") & (play_df.fumble == True) &
                (play_df.change_of_poss == 0)
            ],
            [
                "Punt Team Fumble Recovery"
            ], default = play_df['type.text']
        )
        play_df['type.text'] = np.select(
            [
                (play_df['type.text'].isin(["Punt Touchdown"]))|
                ((play_df['scoringPlay']==True) & (play_df["punt_play"] == True) & (play_df.change_of_poss == 0))
            ],
            [
                "Punt Team Fumble Recovery Touchdown"
            ], default = play_df['type.text']
        )
        play_df['type.text'] = np.where(
            play_df['type.text'].isin(["Kickoff Touchdown"]),
            "Kickoff Team Fumble Recovery Touchdown", play_df['type.text']
        )
        play_df['type.text'] = np.where(
            (play_df['type.text'].isin(["Fumble Return Touchdown"])) &
            ((play_df["pass"] == True) | (play_df["rush"] == True)),
            "Fumble Recovery (Opponent) Touchdown", play_df['type.text']
        )

        #--- Safeties (kickoff, punt, penalty) ----
        play_df['type.text'] = np.where(
            (play_df['type.text'].isin(["Pass Reception", "Rush", "Rushing Touchdown"]) &
             ((play_df["pass"] == True) | (play_df["rush"] == True)) &
             (play_df["safety"] == True)),
            "Safety", play_df["type.text"]
        )
        play_df['type.text'] = np.where(
            (play_df.kickoff_safety == True),
            "Kickoff (Safety)", play_df['type.text']
        )
        play_df['type.text'] = np.where(
            (play_df.punt_safety == True),
            "Punt (Safety)", play_df['type.text']
        )
        play_df['type.text'] = np.where(
            (play_df.penalty_safety == True),
            "Penalty (Safety)", play_df['type.text']
        )
        play_df['type.text'] = np.where(
                (play_df['type.text'] == 'Extra Point Good') &
                (play_df["text"].str.contains("Two-Point", case=False, flags=0, na=False, regex=True)),
                "Two-Point Conversion Good", play_df['type.text']
        )
        play_df['type.text'] = np.where(
                (play_df['type.text'] == 'Extra Point Missed') &
                (play_df["text"].str.contains("Two-Point", case=False, flags=0, na=False, regex=True)),
                "Two-Point Conversion Missed", play_df['type.text']
        )
    #--------------------------------------------------
        play_df = self.setup_penalty_data(play_df)
        #--------------------------------------------------
        return play_df

    def add_play_category_flags(self, play_df):
        #--- Sacks ----
        play_df['sack'] = np.select(
            [
                play_df['type.text'].isin(["Sack"]),
                (play_df['type.text'].isin(["Fumble Recovery (Own)", "Fumble Recovery (Own) Touchdown", "Fumble Recovery (Opponent)", "Fumble Recovery (Opponent) Touchdown"])) &
                (play_df['pass'] == True) & (play_df["text"].str.contains("sacked", case=False, flags=0, na=False, regex=True)),
                ((play_df['type.text'].isin(["Safety"])) & (play_df["text"].str.contains("sacked", case=False, flags=0, na=False, regex=True)))
            ],
            [
                True,
                True,
                True
            ], default = False
        )
        #--- Interceptions ------
        play_df["int"] = play_df["type.text"].isin(["Interception Return", "Interception Return Touchdown"])
        play_df["int_td"] = play_df["type.text"].isin(["Interception Return Touchdown"])

        #--- Pass Completions, Attempts and Targets -------
        play_df['complete_pass'] = ((play_df['type.text'].isin(["Pass Reception", "Pass Completion", "Passing Touchdown"])) |
                                 (play_df['type.text'].isin(["Fumble Recovery (Own)", "Fumble Recovery (Own) Touchdown", "Fumble Recovery (Opponent)", "Fumble Recovery (Opponent) Touchdown"]) &
                                  play_df['pass'] == True & ~play_df["text"].str.contains("sacked", case=False, flags=0, na=False, regex=True)))

        play_df['pass_attempt'] = ((play_df['type.text'].isin(["Pass Reception", "Pass Completion", "Passing Touchdown", "Pass Incompletion"])) |
                                   (play_df['type.text'].isin(["Fumble Recovery (Own)", "Fumble Recovery (Own) Touchdown", "Fumble Recovery (Opponent)", "Fumble Recovery (Opponent) Touchdown"]) &
                                    play_df['pass'] == True & ~play_df["text"].str.contains("sacked", case=False, flags=0, na=False, regex=True)))

        play_df['target'] = ((play_df['type.text'].isin(["Pass Reception", "Pass Completion", "Passing Touchdown", "Pass Incompletion"])) |
                             (play_df['type.text'].isin(["Fumble Recovery (Own)", "Fumble Recovery (Own) Touchdown", "Fumble Recovery (Opponent)", "Fumble Recovery (Opponent) Touchdown"]) &
                              play_df['pass'] == True & ~play_df["text"].str.contains("sacked", case=False, flags=0, na=False, regex=True)))
        play_df['pass_breakup'] = play_df['text'].str.contains('broken up by', case=False, flags=0, na=False, regex=True)
        #--- Pass/Rush TDs ------
        play_df['pass_touchdown'] = (play_df["type.text"] == "Passing Touchdown") | ((play_df["pass"] == True) & (play_df["td_play"] == True))
        play_df['rush_touchdown'] = (play_df["type.text"] == "Rushing Touchdown") | ((play_df["rush"] == True) & (play_df["td_play"] == True))
        #--- Change of possession via turnover
        play_df['turnover_vec'] = play_df["type.text"].isin(turnover_vec)
        play_df['offense_score_play'] = play_df["type.text"].isin(offense_score_vec)
        play_df['defense_score_play'] = play_df["type.text"].isin(defense_score_vec)
        play_df['downs_turnover'] = np.where(
            (play_df["type.text"].isin(normalplay)) &
            (play_df["statYardage"] < play_df["start.ydstogo"]) &
            (play_df["start.down"] == 4) &
            (play_df["penalty_1st_conv"] == False),
            True, False
        )
        #--- Touchdowns----
        play_df['scoring_play'] = play_df["type.text"].isin(scores_vec)
        play_df['yds_punted'] = play_df["text"].str.extract(r"(?<= punt for)[^,]+(\d+)", flags=re.IGNORECASE).astype(float)
        play_df['yds_punt_gained'] = np.where(play_df.punt == True, play_df["statYardage"], None)
        play_df['field_goal_attempt'] =  np.where(
            (play_df["type.text"].str.contains("Field Goal", case=False, flags=0, na=False, regex=True))|
            (play_df["text"].str.contains("Field Goal", case=False, flags=0, na=False, regex=True)),
            True, False
        )
        play_df['fg_made'] = (play_df["type.text"] == "Field Goal Good")
        play_df['yds_fg'] = play_df["text"].str.extract(r"(\\d{0,2}\s?)Yd|(\\d{0,2}\s?)Yard FG|(\\d{0,2}\s?)Field|(\\d{0,2}\s?)Yard Field",
                                                        flags=re.IGNORECASE).bfill(axis=1)[0].astype(float)
        #--------------------------------------------------
        play_df['start.yardline_100'] = np.where(
            play_df['field_goal_attempt'] == True,
            play_df['yds_fg'] - 17, play_df["start.yardline_100"]
        )
        play_df["start.yardline_100"] = np.select(
            [
                (play_df["start.yardline_100"].isna()) &
                (~play_df["type.text"].isin(kickoff_vec)) &
                (play_df['start.posteam.id'] == play_df["homeTeamId"]),
                (play_df["start.yardline_100"].isna()) &
                (~play_df["type.text"].isin(kickoff_vec)) &
                (play_df['start.posteam.id'] == play_df["awayTeamId"])
            ],
            [
                100-play_df["start.yardLine"].astype(float),
                play_df["start.yardLine"].astype(float)
            ], default = play_df["start.yardline_100"]
        )
        play_df["pos_unit"] = np.select(
            [
                play_df.punt == True,
                play_df.kickoff_play == True,
                play_df.field_goal_attempt == True,
                play_df["type.text"] == "Defensive 2pt Conversion"
            ],
            [
                'Punt Offense',
                'Kickoff Return',
                'Field Goal Offense',
                'Offense'
            ],
            default='Offense'
        )
        play_df["def_pos_unit"] = np.select(
            [
                play_df.punt == True,
                play_df.kickoff_play == True,
                play_df.field_goal_attempt == True,
                play_df["type.text"] == "Defensive 2pt Conversion"
            ],
            [
                'Punt Return',
                'Kickoff Defense',
                'Field Goal Defense',
                'Defense'
            ],
            default='Defense'
        )
        #--- Lags/Leads play type ----
        play_df['lead_play_type'] = play_df['type.text'].shift(-1)

        play_df['special_teams'] = np.where(
           (play_df.field_goal_attempt == True) | (play_df.punt == True) | (play_df.kickoff_play == True), True, False
        )
        play_df['play'] = np.where(
            (~play_df['type.text'].isin(['Timeout','End Period', 'End of Half','Penalty'])), True, False
        )
        play_df['scrimmage_play'] = np.where(
            (play_df.special_teams == False) &
            (~play_df['type.text'].isin(['Timeout','Extra Point Good','Extra Point Missed','Two-Point Pass','Two-Point Rush'])),
            True, False
        )
        #--------------------------------------------------
        #--- Change of posteam by lead('posteam', 1)----
        play_df['change_of_posteam'] = np.where(
            (play_df.posteam == play_df.lead_posteam) & (~(play_df.lead_play_type.isin(["End Period", "End of Half"])) | play_df.lead_play_type.isna() == True),
            False,
            np.where(
                (play_df.posteam == play_df.lead_posteam2) &
                ((play_df.lead_play_type.isin(["End Period", "End of Half"])) | play_df.lead_play_type.isna() == True),
                False, True
            )
        )
        play_df['change_of_posteam'] = np.where(play_df['change_of_poss'].isna(), False, play_df['change_of_posteam'])
        play_df["posteam_score_differential_end"] = np.where(
            (play_df["type.text"].isin(end_change_vec)) | (play_df.downs_turnover == True),
            -1*play_df.posteam_score_differential,  play_df.posteam_score_differential
        )
        play_df['posteam_score_differential_end'] = np.select(
            [
                (abs(play_df.posteam_score_pts) >= 8) & (play_df.scoring_play == False) & (play_df.change_of_posteam == False),
                (abs(play_df.posteam_score_pts) >= 8) & (play_df.scoring_play == False) & (play_df.change_of_posteam == True)
            ],
            [
                play_df['posteam_score_differential'], -1*play_df['posteam_score_differential']
            ], default = play_df['posteam_score_differential_end']
        )
        play_df['drive_result_detailed'] = np.select(
            [
                play_df.downs_turnover == 1,
                (play_df["type.text"] == "Punt")|(play_df["type.text"] == "Punt Return"),
                (play_df["type.text"] == "Punt (Safety)") & (play_df['safety'] == True),
                play_df["type.text"] == "Blocked Punt (Safety)",
                (play_df["type.text"] == "Blocked Punt") & (play_df['safety'] == True),
                play_df["type.text"] == "Blocked Punt",
                play_df["type.text"] == "Blocked Punt Touchdown",
                play_df["type.text"] == "Punt Touchdown",
                play_df["type.text"] == "Punt Team Fumble Recovery Touchdown",
                play_df["type.text"] == "Punt Return Touchdown",
                play_df["type.text"] == "Fumble Recovery (Opponent) Touchdown",
                play_df["type.text"] == "Fumble Return Touchdown",
                play_df["type.text"] == "Fumble Recovery (Opponent)",
                play_df["type.text"] == "Fumble Recovery (Own) Touchdown",
                play_df["type.text"] == "Interception Return Touchdown",
                play_df["type.text"] == "Interception Return",
                play_df["type.text"] == "Sack Touchdown",
                (play_df["type.text"] == "Safety") & (play_df["kickoff_play"] == 0),
                (play_df["type.text"] == "Kickoff (Safety)") & (play_df["kickoff_safety"] == 1),
                (play_df["type.text"] == "Kickoff") & (play_df["kickoff_safety"] == 1),
                play_df["type.text"] == "Kickoff Return Touchdown",
                play_df["type.text"] == "Kickoff Touchdown",
                play_df["type.text"] == "Kickoff Team Fumble Recovery",
                play_df["type.text"] == "Kickoff Team Fumble Recovery Touchdown",
                play_df["type.text"] == "Penalty (Safety)",
                play_df["type.text"] == "Passing Touchdown",
                play_df["type.text"] == "Pass Reception Touchdown",
                (play_df["type.text"] == "Pass Completion") & (play_df['pass_touchdown'] == True),
                play_df["type.text"] == "Rushing Touchdown",
                (play_df["type.text"] == "Rush") & (play_df['rush_touchdown'] == True),
                play_df["type.text"] == "Field Goal Good",
                play_df["type.text"] == "Field Goal Missed",
                play_df["type.text"] == "Missed Field Goal Return",
                play_df["type.text"] == "Blocked Field Goal Touchdown",
                play_df["type.text"] == "Missed Field Goal Return Touchdown",
                play_df["type.text"] == "Blocked Field Goal",
                play_df["type.text"] == "Uncategorized Touchdown",
                play_df["type.text"] == "End of Half",
                play_df["type.text"] == "End of Game",
                play_df["type.text"] == "End Half"
            ],
            [
                "Downs Turnover",
                "Punt",
                "Safety",
                "Safety",
                "Safety",
                "Blocked Punt",
                "Blocked Punt Touchdown",
                "Punt Team Fumble Recovery Touchdown",
                "Punt Team Fumble Recovery Touchdown",
                "Punt Return Touchdown",
                "Fumble Recovery (Opponent) Touchdown",
                "Fumble Return Touchdown",
                "Fumble Recovery (Opponent)",
                "Fumble Recovery (Own) Touchdown",
                "Interception Return Touchdown",
                "Interception Return",
                "Sack Touchdown",
                "Safety",
                "Kickoff (Safety)",
                "Kickoff (Safety)",
                "Kickoff Return Touchdown",
                "Kickoff Touchdown",
                "Kickoff Team Fumble Recovery",
                "Kickoff Team Fumble Recovery Touchdown",
                "Safety",
                "Passing Touchdown",
                "Passing Touchdown",
                "Passing Touchdown",
                "Rushing Touchdown",
                "Rushing Touchdown",
                "Field Goal Good",
                "Field Goal Missed",
                "Missed Field Goal Return",
                "Blocked Field Goal Touchdown",
                "Missed Field Goal Return Touchdown",
                "Blocked Field Goal",
                "Uncategorized Touchdown",
                "End of Half",
                "End of Game",
                "End Half"
            ], default = None
        )
        play_df['drive_points'] = np.select(
            [
                play_df.downs_turnover == 1,
                (play_df["type.text"] == "Punt")|(play_df["type.text"] == "Punt Return"),
                (play_df["type.text"] == "Punt (Safety)") & (play_df['safety'] == True),
                play_df["type.text"] == "Blocked Punt (Safety)",
                (play_df["type.text"] == "Blocked Punt") & (play_df['safety'] == True),
                play_df["type.text"] == "Blocked Punt",
                play_df["type.text"] == "Blocked Punt Touchdown",
                play_df["type.text"] == "Punt Touchdown",
                play_df["type.text"] == "Punt Team Fumble Recovery Touchdown",
                play_df["type.text"] == "Punt Return Touchdown",
                play_df["type.text"] == "Fumble Recovery (Opponent) Touchdown",
                play_df["type.text"] == "Fumble Return Touchdown",
                play_df["type.text"] == "Fumble Recovery (Opponent)",
                play_df["type.text"] == "Fumble Recovery (Own) Touchdown",
                play_df["type.text"] == "Interception Return Touchdown",
                play_df["type.text"] == "Interception Return",
                play_df["type.text"] == "Sack Touchdown",
                (play_df["type.text"] == "Safety") & (play_df["kickoff_play"] == 0),
                (play_df["type.text"] == "Kickoff (Safety)") & (play_df["kickoff_safety"] == 1),
                (play_df["type.text"] == "Kickoff") & (play_df["kickoff_safety"] == 1),
                play_df["type.text"] == "Kickoff Return Touchdown",
                play_df["type.text"] == "Kickoff Touchdown",
                play_df["type.text"] == "Kickoff Team Fumble Recovery",
                play_df["type.text"] == "Kickoff Team Fumble Recovery Touchdown",
                play_df["type.text"] == "Penalty (Safety)",
                play_df["type.text"] == "Passing Touchdown",
                play_df["type.text"] == "Pass Reception Touchdown",
                (play_df["type.text"] == "Pass Completion") & (play_df['pass_touchdown'] == True),
                play_df["type.text"] == "Rushing Touchdown",
                (play_df["type.text"] == "Rush") & (play_df['rush_touchdown'] == True),
                play_df["type.text"] == "Field Goal Good",
                play_df["type.text"] == "Field Goal Missed",
                play_df["type.text"] == "Missed Field Goal Return",
                play_df["type.text"] == "Blocked Field Goal Touchdown",
                play_df["type.text"] == "Missed Field Goal Return Touchdown",
                play_df["type.text"] == "Blocked Field Goal",
                play_df["type.text"] == "Uncategorized Touchdown",
                play_df["type.text"] == "End of Half",
                play_df["type.text"] == "End of Game",
                play_df["type.text"] == "End Half"
            ],
            [
                0,
                0,
                -2,
                -2,
                -2,
                0,
                -7,
                7,
                7,
                -7,
                -7,
                -7,
                0,
                7,
                -7,
                0,
                -7,
                -2,
                -2,
                -2,
                7,
                -7,
                0,
                -7,
                -2,
                7,
                7,
                7,
                7,
                7,
                3,
                0,
                0,
                -7,
                -7,
                0,
                7,
                0,
                0,
                0
            ], default = None
        )

        drive_df = play_df.groupby('drive.id')['drive_result_detailed']
        drive_df = drive_df.fillna(method='bfill')
        drive_scores_df = play_df.groupby('drive.id')['drive_points']
        drive_scores_df = drive_scores_df.fillna(method='bfill')

        play_df['drive_result_detailed'] = drive_df
        play_df['lag_drive_result_detailed'] = play_df.drive_result_detailed.shift(1)
        play_df['lag_drive_points'] = play_df.drive_points.shift(1)
        play_df['drive_result_detailed'] = np.select([
                (play_df['type.text'] == "Extra Point Good") |
                (play_df['type.text'] == "Extra Point Missed") |
                (play_df['type.text'] == "Two Point Pass") |
                (play_df['type.text'] == "Two Point Rush")
            ],
            [
                play_df['lag_drive_result_detailed']
            ], default = play_df['drive_result_detailed']
        )
        play_df['drive_points'] = np.select([
                (play_df['type.text'] == "Extra Point Good") |
                (play_df['type.text'] == "Extra Point Missed") |
                (play_df['type.text'] == "Two Point Pass") |
                (play_df['type.text'] == "Two Point Rush")
            ],
            [
                play_df['lag_drive_points']
            ], default = play_df['drive_points']
        )
        play_df['drive_points'] = play_df.drive_points.fillna(method='bfill')
        return play_df

    def add_yardage_cols(self, play_df):
        play_df['yds_rushed'] = None
        play_df['yds_rushed'] = np.select(
            [
                (play_df.rush == True) & (play_df.text.str.contains("run for no gain", case=False, flags=0, na=False, regex=True)),
                (play_df.rush == True) & (play_df.text.str.contains("for no gain", case=False, flags=0, na=False, regex=True)),
                (play_df.rush == True) & (play_df.text.str.contains("run for a loss of", case=False, flags=0, na=False, regex=True)),
                (play_df.rush == True) & (play_df.text.str.contains("rush for a loss of", case=False, flags=0, na=False, regex=True)),
                (play_df.rush == True) & (play_df.text.str.contains("run for", case=False, flags=0, na=False, regex=True)),
                (play_df.rush == True) & (play_df.text.str.contains("rush for", case=False, flags=0, na=False, regex=True)),
                (play_df.rush == True) & (play_df.text.str.contains("Yd Run", case=False, flags=0, na=False, regex=True)),
                (play_df.rush == True) & (play_df.text.str.contains("Yd Rush", case=False, flags=0, na=False, regex=True)),
                (play_df.rush == True) & (play_df.text.str.contains("Yard Rush", case=False, flags=0, na=False, regex=True)),
                (play_df.rush == True) & (play_df.text.str.contains("rushed", case=False, flags=0, na=False, regex=True)) &
                (~play_df.text.str.contains("touchdown", case=False, flags=0, na=False, regex=True)),
                (play_df.rush == True) & (play_df.text.str.contains("rushed", case=False, flags=0, na=False, regex=True)) &
                (play_df.text.str.contains("touchdown", case=False, flags=0, na=False, regex=True))
            ],
            [
                0.0,
                0.0,
                -1 * play_df.text.str.extract(r"((?<=run for a loss of)[^,]+)", flags=re.IGNORECASE)[0].str.extract(r"(\d+)")[0].astype(float),
                -1 * play_df.text.str.extract(r"((?<=rush for a loss of)[^,]+)", flags=re.IGNORECASE)[0].str.extract(r"(\d+)")[0].astype(float),
                play_df.text.str.extract(r"((?<=run for)[^,]+)", flags=re.IGNORECASE)[0].str.extract(r"(\d+)")[0].astype(float),
                play_df.text.str.extract(r"((?<=rush for)[^,]+)", flags=re.IGNORECASE)[0].str.extract(r"(\d+)")[0].astype(float),
                play_df.text.str.extract(r"(\d+) Yd Run", flags=re.IGNORECASE)[0].astype(float),
                play_df.text.str.extract(r"(\d+) Yd Rush", flags=re.IGNORECASE)[0].astype(float),
                play_df.text.str.extract(r"(\d+) Yard Rush", flags=re.IGNORECASE)[0].astype(float),
                play_df.text.str.extract(r"for (\d+) yards", flags=re.IGNORECASE)[0].astype(float),
                play_df.text.str.extract(r"for a (\d+) yard", flags=re.IGNORECASE)[0].astype(float)
            ], default = None)

        play_df['yds_receiving'] = None
        play_df['yds_receiving'] = np.select(
            [
                (play_df["pass"] == True) & (play_df.text.str.contains("complete to", case=False)) & (play_df.text.str.contains(r"for no gain", case=False)),
                (play_df["pass"] == True) & (play_df.text.str.contains("complete to", case=False)) & (play_df.text.str.contains("for a loss", case=False)),
                (play_df["pass"] == True) & (play_df.text.str.contains("complete to", case=False)),
                (play_df["pass"] == True) & (play_df.text.str.contains("complete to", case=False))
            ],
            [
                0.0,
                -1 * play_df.text.str.extract(r"((?<=for a loss of)[^,]+)", flags=re.IGNORECASE)[0].str.extract(r"(\d+)")[0].astype(float),
                play_df.text.str.extract(r"((?<=for)[^,]+)", flags=re.IGNORECASE)[0].str.extract(r"(\d+)")[0].astype(float),
                play_df.text.str.extract(r"((?<=for)[^,]+)", flags=re.IGNORECASE)[0].str.extract(r"(\d+)")[0].astype(float)
            ], default = None
        )

        play_df['yds_int_return'] = None
        play_df['yds_int_return'] = np.select(
            [
                (play_df["pass"] == True) & (play_df["int_td"] == True) & (play_df.text.str.contains("Yd Interception Return", case=False)),
                (play_df["pass"] == True) & (play_df["int"] == True) & (play_df.text.str.contains(r"for no gain", case=False)),
                (play_df["pass"] == True) & (play_df["int"] == True) & (play_df.text.str.contains(r"for a loss of", case=False)),
                (play_df["pass"] == True) & (play_df["int"] == True) & (play_df.text.str.contains(r"for a TD", case=False)),
                (play_df["pass"] == True) & (play_df["int"] == True) & (play_df.text.str.contains(r"return for", case=False)),
                (play_df["pass"] == True) & (play_df["int"] == True)
            ],
            [
                play_df.text.str.extract(r"(.+) Interception Return", flags=re.IGNORECASE)[0].str.extract(r"(\d+)")[0].astype(float),
                0.0,
                -1 * play_df.text.str.extract(r"((?<= for a loss of)[^,]+)", flags=re.IGNORECASE)[0].str.extract(r"(\d+)")[0].astype(float),
                play_df.text.str.extract(r"((?<= return for)[^,]+)", flags=re.IGNORECASE)[0].str.extract(r"(\d+)")[0].astype(float),
                play_df.text.str.extract(r"((?<= return for)[^,]+)", flags=re.IGNORECASE)[0].str.extract(r"(\d+)")[0].astype(float),
                play_df.text.str.replace("for a 1st", "").str.extract(r"((?<=for)[^,]+)", flags=re.IGNORECASE)[0].str.extract(r"(\d+)")[0].astype(float)
            ], default = None
        )

        #     play_df['yds_fumble_return'] = None
        #     play_df['yds_penalty'] = None

        play_df['yds_kickoff'] = None
        play_df['yds_kickoff'] = np.where(
            (play_df["kickoff_play"] == True),
            play_df.text.str.extract(r"((?<= kickoff for)[^,]+)", flags=re.IGNORECASE)[0].str.extract(r"(\d+)")[0].astype(float),
            play_df['yds_kickoff']
        )

        play_df['yds_kickoff_return'] = None
        play_df['yds_kickoff_return'] = np.select(
            [
                (play_df.kickoff_play == True) & (play_df.kickoff_tb == True) & (play_df.season > 2013),
                (play_df.kickoff_play == True) & (play_df.kickoff_tb == True) & (play_df.season <= 2013),
                (play_df.kickoff_play == True) & (play_df.fumble == False) & (play_df.text.str.contains(r"for no gain|fair catch|fair caught", regex=True,case = False)),
                (play_df.kickoff_play == True) & (play_df.fumble == False) & (play_df.text.str.contains(r"out-of-bounds|out of bounds", regex=True,case = False)),
                ((play_df.kickoff_downed == True) | (play_df.kickoff_fair_catch == True)),
                (play_df.kickoff_play == True) & (play_df.text.str.contains(r"returned by", regex=True,case = False)),
                (play_df.kickoff_play == True) & (play_df.text.str.contains(r"return for", regex=True,case = False)),
                (play_df.kickoff_play == True)
            ],
            [
                25,
                20,
                0,
                40,
                0,
                play_df.text.str.extract(r"((?<= for)[^,]+)", flags=re.IGNORECASE)[0].str.extract(r"(\d+)")[0].astype(float),
                play_df.text.str.extract(r"((?<= return for)[^,]+)", flags=re.IGNORECASE)[0].str.extract(r"(\d+)")[0].astype(float),
                play_df.text.str.extract(r"((?<= returned for)[^,]+)", flags=re.IGNORECASE)[0].str.extract(r"(\d+)")[0].astype(float),
            ], default = play_df['yds_kickoff_return']
        )

        play_df['yds_punted'] = None
        play_df['yds_punted'] = np.select(
            [
                (play_df.punt == True) & (play_df.punt_blocked == True),
                (play_df.punt == True)
            ],
            [
                0,
                play_df.text.str.extract(r"((?<= punt for)[^,]+)", flags=re.IGNORECASE)[0].str.extract(r"(\d+)")[0].astype(float)
            ], default = play_df.yds_punted
        )

        play_df['yds_punt_return'] = np.select(
            [
                (play_df.punt == True) & (play_df.punt_tb == 1),
                (play_df.punt == True) & (play_df["text"].str.contains(r"fair catch|fair caught", case=False, flags=0, na=False, regex=True)),
                (play_df.punt == True) & ((play_df.punt_downed == True) | (play_df.punt_oob == True) | (play_df.punt_fair_catch == True)),
                (play_df.punt == True) & (play_df["text"].str.contains(r"no return", case=False, flags=0, na=False, regex=True)),
                (play_df.punt == True) & (play_df["text"].str.contains(r"returned \d+ yards", case=False, flags=0, na=False, regex=True)),
                (play_df.punt == True) & (play_df.punt_blocked == False),
                (play_df.punt == True) & (play_df.punt_blocked == True)
            ],
            [
                20,
                0,
                0,
                0,
                play_df.text.str.extract(r"((?<= returned)[^,]+)", flags=re.IGNORECASE)[0].str.extract(r"(\d+)")[0].astype(float),
                play_df.text.str.extract(r"((?<= returns for)[^,]+)", flags=re.IGNORECASE)[0].str.extract(r"(\d+)")[0].astype(float),
                play_df.text.str.extract(r"((?<= return for)[^,]+)", flags=re.IGNORECASE)[0].str.extract(r"(\d+)")[0].astype(float)
            ], default=None
        )

        play_df['yds_fumble_return'] = np.select(
            [
                (play_df.fumble == True) & (play_df.kickoff_play == False)
            ],
            [
                play_df.text.str.extract(r"((?<= return for)[^,]+)", flags=re.IGNORECASE)[0].str.extract(r"(\d+)")[0].astype(float)
            ], default=None
        )

        play_df['yds_sacked'] = np.select(
            [
                (play_df.sack == True)
            ],
            [
                -1 * play_df.text.str.extract(r"((?<= sacked)[^,]+)", flags=re.IGNORECASE)[0].str.extract(r"(\d+)")[0].astype(float)
            ], default=None
        )

        play_df['yds_penalty'] = np.select(
            [
                (play_df.penalty_detail == 1)
            ],
            [
                -1 * play_df.text.str.extract(r"((?<= sacked)[^,]+)", flags=re.IGNORECASE)[0].str.extract(r"(\d+)")[0].astype(float)
            ], default=None
        )

        play_df['yds_penalty'] = np.select(
            [
                play_df.penalty_detail.isin(["Penalty Declined","Penalty Offset"]),
                play_df.yds_penalty.notna(),
                (play_df.penalty_detail.notna()) & (play_df.yds_penalty.isna()) & (play_df.rush == True),
                (play_df.penalty_detail.notna()) & (play_df.yds_penalty.isna()) & (play_df.int == True),
                (play_df.penalty_detail.notna()) & (play_df.yds_penalty.isna()) & (play_df["pass"] == 1) & (play_df["sack"] == False) & (play_df["type.text"] != "Pass Incompletion"),
                (play_df.penalty_detail.notna()) & (play_df.yds_penalty.isna()) & (play_df["pass"] == 1) & (play_df["sack"] == False) & (play_df["type.text"] == "Pass Incompletion"),
                (play_df.penalty_detail.notna()) & (play_df.yds_penalty.isna()) & (play_df["pass"] == 1) & (play_df["sack"] == True),
                (play_df["type.text"] == "Penalty")
            ],
            [
                0,
                play_df.yds_penalty.astype(float),
                play_df.statYardage.astype(float) - play_df.yds_rushed.astype(float),
                play_df.statYardage.astype(float) - play_df.yds_int_return.astype(float),
                play_df.statYardage.astype(float) - play_df.yds_receiving.astype(float),
                play_df.statYardage.astype(float),
                play_df.statYardage.astype(float) - play_df.yds_sacked.astype(float),
                play_df.statYardage.astype(float)
            ], default=None
        )
        play_df['kick_distance'] = play_df[['yds_fg', 'yds_punted', 'yds_kickoff']].bfill(axis=1).iloc[:, 0]
        return play_df

    def add_player_cols(self, play_df):
        play_df['rush_player'] = None
        play_df['receiver_player'] = None
        play_df['pass_player'] = None
        play_df['sack_players'] = None
        play_df['sack_player1'] = None
        play_df['sack_player2'] = None
        play_df['interception_player'] = None
        play_df['pass_breakup_player'] = None
        play_df['fg_kicker_player'] = None
        play_df['fg_return_player'] = None
        play_df['fg_block_player'] = None
        play_df['punter_player'] = None
        play_df['punt_return_player'] = None
        play_df['punt_block_player'] = None
        play_df['punt_block_return_player'] = None
        play_df['kickoff_player'] = None
        play_df['kickoff_return_player'] = None
        play_df['fumble_player'] = None
        play_df['fumble_forced_player'] = None
        play_df['fumble_recovered_player'] = None
        play_df['rush_player_name'] = None
        play_df['receiver_player_name'] = None
        play_df['passer_player_name'] = None
        play_df['sack_player_name'] = None
        play_df['sack_player_name2'] = None
        play_df['interception_player_name'] = None
        play_df['pass_breakup_player_name'] = None
        play_df['fg_kicker_player_name'] = None
        play_df['fg_return_player_name'] = None
        play_df['fg_block_player_name'] = None
        play_df['punter_player_name'] = None
        play_df['punt_return_player_name'] = None
        play_df['punt_block_player_name'] = None
        play_df['punt_block_return_player_name'] = None
        play_df['kickoff_player_name'] = None
        play_df['kickoff_return_player_name'] = None
        play_df['fumble_player_name'] = None
        play_df['fumble_forced_player_name'] = None
        play_df['fumble_recovered_player_name'] = None

        ## Extract player names
        # RB names
        play_df['rush_player'] = np.where(
            (play_df.rush == 1),
            play_df.text.str.extract(r"(.{0,25} )run |(.{0,25} )\d{0,2} Yd Run|(.{0,25} )rush |(.{0,25} )rushed ").bfill(axis=1)[0],
            None
        )
        play_df['rush_player'] = play_df.rush_player.str.replace(r" run | \d+ Yd Run| rush ", "", regex=True)
        play_df['rush_player'] = play_df.rush_player.str.replace(" \((.+)\)", "", regex=True)

        # QB names
        play_df['pass_player'] = np.where(
            (play_df["pass"] == 1) & (play_df["type.text"] != "Passing Touchdown"),
            play_df.text.str.extract(r"pass from (.*?) \(|(.{0,30} )pass |(.+) sacked by|(.+) sacked for|(.{0,30} )incomplete ").bfill(axis=1)[0],
            play_df['pass_player']
        )
        play_df['pass_player'] = play_df.pass_player.str.replace("pass | sacked by| sacked for| incomplete", "", regex=True)

        play_df['pass_player'] = np.where(
            (play_df["pass"] == 1) & (play_df["type.text"] == "Passing Touchdown"),
            play_df.text.str.extract("pass from(.+)")[0],
            play_df['pass_player']
        )
        play_df['pass_player'] = play_df.pass_player.str.replace("pass from", "", regex=True)
        play_df['pass_player'] = play_df.pass_player.str.replace(r"\(.+\)", "", regex=True)
        play_df['pass_player'] = play_df.pass_player.str.replace(r" \,", "", regex=True)

        play_df['pass_player'] = np.where(
            (play_df["type.text"] == "Passing Touchdown") & play_df.pass_player.isna(),
            play_df.text.str.extract("(.+)pass (.+) complete to")[0],
            play_df['pass_player']
        )
        play_df['pass_player'] = play_df.pass_player.str.replace(r" pass complete to(.+)", "", regex=True)
        play_df['pass_player'] = play_df.pass_player.str.replace(r" pass complete to", "", regex=True)

        play_df['pass_player'] = np.where(
            (play_df["type.text"] == "Passing Touchdown") & play_df.pass_player.isna(),
            play_df.text.str.extract(r"(.+)pass,to")[0],
            play_df['pass_player']
        )

        play_df['pass_player'] = play_df.pass_player.str.replace(r" pass,to(.+)", "", regex=True)
        play_df['pass_player'] = play_df.pass_player.str.replace(r" pass,to", "", regex=True)
        play_df['pass_player'] = play_df.pass_player.str.replace(r" \((.+)\)", "", regex=True)


        play_df['receiver_player'] = np.where(
            (play_df["pass"] == 1) & ~play_df.text.str.contains(r"sacked", case=False, flags=0, na=False, regex=True),
            play_df.text.str.extract(r"to (.+)")[0],
            None
        )

        play_df['receiver_player'] = np.where(
            play_df.text.str.contains("Yd pass", case=False, flags=0, na=False, regex=True),
            play_df.text.str.extract(r"(.{0,25} )\\d{0,2} Yd pass", flags=re.IGNORECASE)[0],
            play_df['receiver_player']
        )

        play_df['receiver_player'] = np.where(
            play_df.text.str.contains(r"Yd TD pass", case=False),
            play_df.text.str.extract(r"(.{0,25} )\\d{0,2} Yd TD pass", flags=re.IGNORECASE)[0],
            play_df['receiver_player']
        )

        play_df['receiver_player'] = np.where(
            (play_df["type.text"] == "Sack")
            | (play_df["type.text"] == "Interception Return")
            | (play_df["type.text"] == "Interception Return Touchdown")
            | (play_df["type.text"].isin(["Fumble Recovery (Opponent) Touchdown","Fumble Recovery (Opponent)"]) & play_df.text.str.contains("sacked", case=False)),
            None,
            play_df['receiver_player']
        )

        play_df.receiver_player = play_df.receiver_player.str.replace("to ", "", case=False,regex=True)
        play_df.receiver_player = play_df.receiver_player.str.replace(r"\\,.+", "", case=False,regex=True)
        play_df.receiver_player = play_df.receiver_player.str.replace(r"for (.+)", "", case=False,regex=True)
        play_df.receiver_player = play_df.receiver_player.str.replace(r" (\d{1,2})", "", case=False,regex=True)
        play_df.receiver_player = play_df.receiver_player.str.replace(r" Yd pass", "", case=False,regex=True)
        play_df.receiver_player = play_df.receiver_player.str.replace(r" Yd TD pass", "", case=False,regex=True)
        play_df.receiver_player = play_df.receiver_player.str.replace(r"pass complete to", "", case=False,regex=True)
        play_df.receiver_player = play_df.receiver_player.str.replace(r"penalty", "", case=False,regex=True)
        play_df.receiver_player = play_df.receiver_player.str.replace(r" \"", "", case=False,regex=True)
        play_df.receiver_player = np.where(
            ~(play_df.receiver_player.str.contains("III", na=False)),
            play_df.receiver_player.str.replace("[A-Z]{3,}","", case=True,regex=True),
            play_df.receiver_player
        )

        play_df.receiver_player = play_df.receiver_player.str.replace(" &", "", case=True,regex=True)
        play_df.receiver_player = play_df.receiver_player.str.replace("A&M", "", case=True,regex=False)
        play_df.receiver_player = play_df.receiver_player.str.replace(" ST", "", case=True,regex=True)
        play_df.receiver_player = play_df.receiver_player.str.replace(" GA", "", case=True,regex=True)
        play_df.receiver_player = play_df.receiver_player.str.replace(" UL", "", case=True,regex=True)
        play_df.receiver_player = play_df.receiver_player.str.replace(" FL", "", case=True,regex=True)
        play_df.receiver_player = play_df.receiver_player.str.replace(" OH", "", case=True,regex=True)
        play_df.receiver_player = play_df.receiver_player.str.replace(" NC", "", case=True,regex=True)
        play_df.receiver_player = play_df.receiver_player.str.replace(" \"", "", case=True,regex=True)
        play_df.receiver_player = play_df.receiver_player.str.replace(" \\u00c9", "", case=True,regex=True)
        play_df.receiver_player = play_df.receiver_player.str.replace(" fumbled,", "", case=False,regex=True)
        play_df.receiver_player = play_df.receiver_player.str.replace("the (.+)", "", case=False,regex=True)
        play_df.receiver_player = play_df.receiver_player.str.replace("pass incomplete to", "", case=False,regex=True)
        play_df.receiver_player = play_df.receiver_player.str.replace("(.+)pass incomplete to", "", case=False,regex=True)
        play_df.receiver_player = play_df.receiver_player.str.replace("(.+)pass incomplete", "", case=False,regex=True)
        play_df.receiver_player = play_df.receiver_player.str.replace("pass incomplete","", case=False,regex=True)
        play_df.receiver_player = play_df.receiver_player.str.replace(" \((.+)\)", "", regex=True)
        play_df.receiver_player = play_df.receiver_player.str.replace(" \(\)", "", regex=True)

        play_df['sack_players'] = np.where(
            (play_df["sack"] == True) | (play_df["fumble"] == True) & (play_df["pass"] == True) ,
            play_df.text.str.extract("sacked by(.+)", flags=re.IGNORECASE)[0],
            play_df.sack_players
        )

        play_df['sack_players'] = play_df.sack_players.str.replace(r"for (.+)","", case=True, regex=True)
        play_df['sack_players'] = play_df.sack_players.str.replace(r"(.+) by ","", case=True, regex=True)
        play_df['sack_players'] = play_df.sack_players.str.replace(r" at the (.+)","", case=True, regex=True)

        play_df['sack_player1'] = play_df.sack_players.str.replace(r"and (.+)","", case=True, regex=True)
        play_df['sack_player2'] = play_df.sack_players.str.extract(r" and(.+)")[0]
        play_df['sack_player2'] = play_df.sack_player2.str.replace(r"(.+) and","", case=True, regex=True)
        play_df['interception_player'] = np.where(
            (play_df["type.text"] == "Interception Return") | (play_df["type.text"] == "Interception Return Touchdown") &
            play_df['pass'] == True, play_df.text.str.extract(r'intercepted (.+)', flags=re.IGNORECASE)[0], 
            play_df.interception_player
        )

        play_df['interception_player'] = np.where(
            play_df.text.str.contains('Yd Interception Return', case=True, regex=True),
            play_df.text.str.extract(r'(.{0,25} )\\d{0,2} Yd Interception Return|(.{0,25} )\\d{0,2} yd interception return', flags=re.IGNORECASE).bfill(axis=1)[0],
            play_df.interception_player
        )
        play_df['interception_player'] = play_df.interception_player.str.replace("return (.+)","", case = True, regex = True)
        play_df['interception_player'] = play_df.interception_player.str.replace("(.+) intercepted","", case = True, regex = True)
        play_df['interception_player'] = play_df.interception_player.str.replace("intercepted","", case = True, regex = True)
        play_df['interception_player'] = play_df.interception_player.str.replace("Yd Interception Return","", regex = True)
        play_df['interception_player'] = play_df.interception_player.str.replace("for a 1st down","", case = True, regex = True)
        play_df['interception_player'] = play_df.interception_player.str.replace("(\\d{1,2})","", case = True, regex = True)
        play_df['interception_player'] = play_df.interception_player.str.replace("for a TD","", case = True, regex = True)
        play_df['interception_player'] = play_df.interception_player.str.replace("at the (.+)","", case = True, regex = True)
        play_df['interception_player'] = play_df.interception_player.str.replace(" by ","", case = True, regex = True)
        play_df['interception_player'] = play_df.interception_player.str.replace("^by ","", case = True, regex = True)
        play_df['interception_player'] = play_df.interception_player.str.replace(" \((.+)\)(.+)", "", regex=True)
        play_df['interception_player'] = play_df.interception_player.str.replace(" \(\)", "", regex=True)

        play_df['pass_breakup_player'] = np.where(
            play_df["pass"] == True, play_df.text.str.extract("broken up by (.+)"), play_df.pass_breakup_player
        )
        play_df['pass_breakup_player'] = play_df.pass_breakup_player.str.replace("(.+) broken up by", "", case = True, regex = True)
        play_df['pass_breakup_player'] = play_df.pass_breakup_player.str.replace("broken up by", "", case = True, regex = True)
        play_df['pass_breakup_player'] = play_df.pass_breakup_player.str.replace("Penalty(.+)", "", case = True, regex = True)
        play_df['pass_breakup_player'] = play_df.pass_breakup_player.str.replace("SOUTH FLORIDA", "", case = True, regex = True)
        play_df['pass_breakup_player'] = play_df.pass_breakup_player.str.replace("WEST VIRGINIA", "", case = True, regex = True)
        play_df['pass_breakup_player'] = play_df.pass_breakup_player.str.replace("MISSISSIPPI ST", "", case = True, regex = True)
        play_df['pass_breakup_player'] = play_df.pass_breakup_player.str.replace("CAMPBELL", "", case = True, regex = True)
        play_df['pass_breakup_player'] = play_df.pass_breakup_player.str.replace("COASTL CAROLINA", "", case = True, regex = True)

        play_df["punter_player"] = np.where(
            play_df['type.text'].str.contains("Punt", regex = True),
            play_df.text.str.extract(r"(.{0,30}) punt|Punt by (.{0,30})", flags=re.IGNORECASE).bfill(axis=1)[0],
            play_df.punter_player
        )
        play_df["punter_player"] = play_df["punter_player"].str.replace(" punt", "", case = False, regex = True)
        play_df["punter_player"] = play_df["punter_player"].str.replace(" for(.+)", "", case = False, regex = True)
        play_df["punter_player"] = play_df["punter_player"].str.replace("Punt by ", "", case = False, regex = True)
        play_df["punter_player"] = play_df["punter_player"].str.replace("\((.+)\)", "", case = False, regex = True)
        play_df["punter_player"] = play_df["punter_player"].str.replace(" returned \d+", "", case = False, regex = True)
        play_df["punter_player"] = play_df["punter_player"].str.replace(" returned", "", case = False, regex = True)
        play_df["punter_player"] = play_df["punter_player"].str.replace(" no return", "", case = False, regex = True)

        play_df["punt_return_player"] = np.where(
            play_df["type.text"].str.contains("Punt",  regex = True),
            play_df.text.str.extract(r", (.{0,25}) returns|fair catch by (.{0,25})|, returned by (.{0,25})|yards by (.{0,30})| return by (.{0,25})", flags=re.IGNORECASE).bfill(axis=1)[0],
            play_df.punt_return_player
        )
        play_df["punt_return_player"] = play_df["punt_return_player"].str.replace(", ", "", case = False, regex = True)
        play_df["punt_return_player"] = play_df["punt_return_player"].str.replace(" returns", "", case = False, regex = True)
        play_df["punt_return_player"] = play_df["punt_return_player"].str.replace(" returned", "", case = False, regex = True)
        play_df["punt_return_player"] = play_df["punt_return_player"].str.replace(" return", "", case = False, regex = True)
        play_df["punt_return_player"] = play_df["punt_return_player"].str.replace("fair catch by", "", case = False, regex = True)
        play_df["punt_return_player"] = play_df["punt_return_player"].str.replace(" at (.+)", "", case = False, regex = True)
        play_df["punt_return_player"] = play_df["punt_return_player"].str.replace(" for (.+)", "", case = False, regex = True)
        play_df["punt_return_player"] = play_df["punt_return_player"].str.replace("(.+) by ", "", case = False, regex = True)
        play_df["punt_return_player"] = play_df["punt_return_player"].str.replace(" to (.+)", "", case = False, regex = True)
        play_df["punt_return_player"] = play_df["punt_return_player"].str.replace("\((.+)\)", "", case = False, regex = True)


        play_df["punt_block_player"] = np.where(
            play_df["type.text"].str.contains("Punt", case = True, regex=True),
            play_df.text.str.extract("punt blocked by (.{0,25})| blocked by(.+)", flags=re.IGNORECASE).bfill(axis=1)[0],
            play_df.punt_block_player
        )
        play_df["punt_block_player"] = play_df["punt_block_player"].str.replace("punt blocked by |for a(.+)", "", case = True, regex = True)
        play_df["punt_block_player"] = play_df["punt_block_player"].str.replace("blocked by(.+)", "", case = True, regex = True)
        play_df["punt_block_player"] = play_df["punt_block_player"].str.replace("blocked(.+)", "", case = True, regex = True)
        play_df["punt_block_player"] = play_df["punt_block_player"].str.replace(" for(.+)", "", case = True, regex = True)
        play_df["punt_block_player"] = play_df["punt_block_player"].str.replace(",(.+)", "", case = True, regex = True)
        play_df["punt_block_player"] = play_df["punt_block_player"].str.replace("punt blocked by |for a(.+)", "", case = True, regex = True)

        play_df["punt_block_player"] = np.where(
            play_df["type.text"].str.contains("yd return of blocked punt"), play_df.text.str.extract("(.+) yd return of blocked"),
            play_df.punt_block_player
        )
        play_df["punt_block_player"] = play_df["punt_block_player"].str.replace("blocked|Blocked", "", regex = True)
        play_df["punt_block_player"] = play_df["punt_block_player"].str.replace("\\d+", "", regex = True)
        play_df["punt_block_player"] = play_df["punt_block_player"].str.replace("yd return of", "", regex = True)

        play_df["punt_block_return_player"] = np.where(
            (play_df["type.text"].str.contains("Punt", case=False, flags=0, na=False, regex=True)) & (play_df.text.str.contains("blocked", case=False, flags=0, na=False, regex=True) & play_df.text.str.contains("return", case=False, flags=0, na=False, regex=True)),
            play_df.text.str.extract("(.+) return"), 
            play_df.punt_block_return_player
        )
        play_df["punt_block_return_player"] = play_df["punt_block_return_player"].str.replace("(.+)blocked by {punt_block_player}","", regex = True)
        play_df["punt_block_return_player"] = play_df["punt_block_return_player"].str.replace("blocked by {punt_block_player}","", regex = True)
        play_df["punt_block_return_player"] = play_df["punt_block_return_player"].str.replace("return(.+)", "", regex = True)
        play_df["punt_block_return_player"] = play_df["punt_block_return_player"].str.replace("return", "", regex = True)
        play_df["punt_block_return_player"] = play_df["punt_block_return_player"].str.replace("(.+)blocked by", "", regex = True)
        play_df["punt_block_return_player"] = play_df["punt_block_return_player"].str.replace("for a TD(.+)|for a SAFETY(.+)", "", regex = True)
        play_df["punt_block_return_player"] = play_df["punt_block_return_player"].str.replace("blocked by", "", regex = True)
        play_df["punt_block_return_player"] = play_df["punt_block_return_player"].str.replace(", ", "", regex = True)

        play_df["kickoff_player"] = np.where(
            play_df["type.text"].str.contains("Kickoff"),
            play_df.text.str.extract("(.{0,25}) kickoff|(.{0,25}) on-side").bfill(axis=1)[0],
            play_df.kickoff_player
        )
        play_df["kickoff_player"] = play_df["kickoff_player"].str.replace(" on-side| kickoff","", regex=True)

        play_df["kickoff_return_player"] = np.where(
            play_df["type.text"].str.contains("ickoff"),
            play_df.text.str.extract(", (.{0,25}) return|, (.{0,25}) fumble|returned by (.{0,25})|touchback by (.{0,25})").bfill(axis=1)[0],
            play_df.kickoff_return_player
        )
        play_df["kickoff_return_player"] = play_df["kickoff_return_player"].str.replace(", ","", case=False, regex=True)
        play_df["kickoff_return_player"] = play_df["kickoff_return_player"].str.replace(" return| fumble| returned by| for (.+)|touchback by ", "", case=False, regex=True)
        play_df["kickoff_return_player"] = play_df["kickoff_return_player"].str.replace("\((.+)\)(.+)", "", case = False, regex = True)

        play_df["fg_kicker_player"] = np.where(
            play_df["type.text"].str.contains("Field Goal"),
            play_df.text.str.extract("(.{0,25} )\\d{0,2} yd field goal| (.{0,25} )\\d{0,2} yd fg|(.{0,25} )\\d{0,2} yard field goal").bfill(axis=1)[0],
            play_df.fg_kicker_player
        )
        play_df["fg_kicker_player"] = play_df["fg_kicker_player"].str.replace(" Yd Field Goal|Yd FG |yd FG| yd FG","", case = False, regex = True)
        play_df["fg_kicker_player"] = play_df["fg_kicker_player"].str.replace("(\\d{1,2})","", case = False, regex = True)

        play_df["fg_block_player"] = np.where(
            play_df["type.text"].str.contains("Field Goal"),
            play_df.text.str.extract("blocked by (.{0,25})"),
            play_df.fg_block_player
        )
        play_df["fg_block_player"] = play_df["fg_block_player"].str.replace(",(.+)", "", case = False, regex = True)
        play_df["fg_block_player"] = play_df["fg_block_player"].str.replace("blocked by ", "", case = False, regex = True)
        play_df["fg_block_player"] = play_df["fg_block_player"].str.replace("  (.)+", "", case = False, regex = True)

        play_df["fg_return_player"] = np.where(
            (play_df["type.text"].str.contains("Field Goal")) &
            (play_df["type.text"].str.contains("blocked by|missed")) &
            (play_df["type.text"].str.contains("return")) ,
            play_df.text.str.extract("  (.+)"),
            play_df.fg_return_player
        )

        play_df["fg_return_player"] = play_df["fg_return_player"].str.replace(",(.+)", "", case=False, regex=True)
        play_df["fg_return_player"] = play_df["fg_return_player"].str.replace("return ", "", case=False, regex=True)
        play_df["fg_return_player"] = play_df["fg_return_player"].str.replace("returned ", "", case=False, regex=True)
        play_df["fg_return_player"] = play_df["fg_return_player"].str.replace(" for (.+)", "", case=False, regex=True)
        play_df["fg_return_player"] = play_df["fg_return_player"].str.replace(" for (.+)", "", case=False, regex=True)

        play_df["fg_return_player"] = np.where(
            play_df["type.text"].isin(["Missed Field Goal Return", "Missed Field Goal Return Touchdown"]),
            play_df.text.str.extract("(.+)return"),
            play_df.fg_return_player
        )
        play_df["fg_return_player"] = play_df["fg_return_player"].str.replace(" return", "", case = False, regex = True)
        play_df["fg_return_player"] = play_df["fg_return_player"].str.replace("(.+),", "", case = False, regex = True)

        if min(play_df["season"])> 2003:
            play_df["fumble_player"] = np.select(
                [
                    
                    play_df.text.str.contains("fumbled by"),
                    play_df.text.str.contains("fumble")
                ],
                [
                    play_df.text.str.extract(r"fumbled by (.{0,25})", flags=re.IGNORECASE).bfill(axis=1)[0],
                    play_df.text.str.extract(r"(.{0,25} )fumble", flags=re.IGNORECASE).bfill(axis=1)[0]
                ], default = play_df.fumble_player
            )
            play_df["fumble_player"] = play_df["fumble_player"].str.replace(r"fumbled by ", "", case = False, regex = True)
            play_df["fumble_player"] = play_df["fumble_player"].str.replace(r" at the (.+)", "", case = False, regex = True)
            play_df["fumble_player"] = play_df["fumble_player"].str.replace(r" fumble(.+)", "", case = False, regex = True)
            play_df["fumble_player"] = play_df["fumble_player"].str.replace(r"fumble", "", case = False, regex = True)
            play_df["fumble_player"] = play_df["fumble_player"].str.replace(r" yds", "", case = False, regex = True)
            play_df["fumble_player"] = play_df["fumble_player"].str.replace(r" yd", "", case = False, regex = True)
            play_df["fumble_player"] = play_df["fumble_player"].str.replace(r"yardline", "", case = False, regex = True)
            play_df["fumble_player"] = play_df["fumble_player"].str.replace(r" yards| yard|for a TD|or a safety", "", case = False, regex = True)
            play_df["fumble_player"] = play_df["fumble_player"].str.replace(r" for ", "", case = False, regex = True)
            play_df["fumble_player"] = play_df["fumble_player"].str.replace(r" a safety", "", case = False, regex = True)
            play_df["fumble_player"] = play_df["fumble_player"].str.replace(r"r no gain", "", case = False, regex = True)
            play_df["fumble_player"] = play_df["fumble_player"].str.replace(r"(.+)(\\d{1,2})", "", case = False, regex = True)
            play_df["fumble_player"] = play_df["fumble_player"].str.replace(r"(\\d{1,2})", "", case = False, regex = True)
            play_df["fumble_player"] = play_df["fumble_player"].str.replace(", ", "", case = False, regex = True)
            play_df["fumble_forced_player"] = np.where(
                (play_df.text.str.contains("fumble", case=False, flags=0, na=False, regex=True)) & 
                (play_df.text.str.contains("forced by", case=False, flags=0, na=False, regex=True)),
                play_df.text.str.extract(r"forced by( .{0,25})", flags=re.IGNORECASE).bfill(axis=1)[0],
                play_df.fumble_forced_player
            )
            play_df["fumble_forced_player"] = play_df["fumble_forced_player"].str.replace(r"(.+)forced by", "", case = False, regex = True)
            play_df["fumble_forced_player"] = play_df["fumble_forced_player"].str.replace(r"forced by", "", case = False, regex = True)
            play_df["fumble_forced_player"] = play_df["fumble_forced_player"].str.replace(r", recove(.+)", "", case = False, regex = True)
            play_df["fumble_forced_player"] = play_df["fumble_forced_player"].str.replace(r", re(.+)", "", case = False, regex = True)
            play_df["fumble_forced_player"] = play_df["fumble_forced_player"].str.replace(r", fo(.+)", "", case = False, regex = True)
            play_df["fumble_forced_player"] = play_df["fumble_forced_player"].str.replace(r", r", "", case = False, regex = True)
            play_df["fumble_forced_player"] = play_df["fumble_forced_player"].str.replace(r", ", "", case = False, regex = True)
            play_df["fumble_recovered_player"] = np.where(
                (play_df.text.str.contains("fumble", case=False, flags=0, na=False, regex=True)) & 
                (play_df.text.str.contains("recovered by", case=False, flags=0, na=False, regex=True)),
                play_df.text.str.extract(r"recovered by( .{0,30}),|recovered by( .{0,30}) to(.+)", flags=re.IGNORECASE).bfill(axis=1)[0],
                play_df.fumble_recovered_player
            )
            play_df["fumble_recovered_player"] = play_df["fumble_recovered_player"].str.replace(" to (.+)", "", case = False, regex = True)
            play_df["fumble_recovered_player"] = play_df["fumble_recovered_player"].str.replace("for a 1ST down", "", case = False, regex = True)
            play_df["fumble_recovered_player"] = play_df["fumble_recovered_player"].str.replace("for a 1st down", "", case = False, regex = True)
            play_df["fumble_recovered_player"] = play_df["fumble_recovered_player"].str.replace("(.+)recovered", "", case = False, regex = True)
            play_df["fumble_recovered_player"] = play_df["fumble_recovered_player"].str.replace("(.+) by", "", case = False, regex = True)
            play_df["fumble_recovered_player"] = play_df["fumble_recovered_player"].str.replace(", recove(.+)", "", case = False, regex = True)
            play_df["fumble_recovered_player"] = play_df["fumble_recovered_player"].str.replace(", re(.+)", "", case = False, regex = True)
            play_df["fumble_recovered_player"] = play_df["fumble_recovered_player"].str.replace("a 1st down", "", case = False, regex = True)
            play_df["fumble_recovered_player"] = play_df["fumble_recovered_player"].str.replace(" a 1st down", "", case = False, regex = True)
            play_df["fumble_recovered_player"] = play_df["fumble_recovered_player"].str.replace(", for(.+)", "", case = False, regex = True)
            play_df["fumble_recovered_player"] = play_df["fumble_recovered_player"].str.replace(" for a", "", case = False, regex = True)
            play_df["fumble_recovered_player"] = play_df["fumble_recovered_player"].str.replace(" fo", "", case = False, regex = True)
            play_df["fumble_recovered_player"] = play_df["fumble_recovered_player"].str.replace(" , r", "", case = False, regex = True)
            play_df["fumble_recovered_player"] = play_df["fumble_recovered_player"].str.replace(", r", "", case = False, regex = True)
            play_df["fumble_recovered_player"] = play_df["fumble_recovered_player"].str.replace("  (.+)", "", case = False, regex = True)
            play_df["fumble_recovered_player"] = play_df["fumble_recovered_player"].str.replace(" ,", "", case = False, regex = True)
            play_df["fumble_recovered_player"] = play_df["fumble_recovered_player"].str.replace("penalty(.+)", "", case = False, regex = True)
            play_df["fumble_recovered_player"] = play_df["fumble_recovered_player"].str.replace("for a 1ST down", "", case = False, regex = True)

        if min(play_df["season"]) <= 2003:
            play_df["fumble_player"] = np.where(
                play_df["text"].str.contains("fumble by"),  
                play_df["text"].str.extract(r"fumble by( .{0,25}),", flags=re.IGNORECASE).bfill(axis=1)[0],
                play_df["fumble_player"]
            )
            play_df["fumble_player"]  = play_df.fumble_player.str.replace(" \((.+)\)", "", regex=True)
            play_df["fumble_player"]  = play_df.fumble_player.str.replace(" \(\)", "", regex=True)
            play_df["fumble_forced_player"] = np.where(
                (play_df.text.str.contains("fumble", case=False, flags=0, na=False, regex=True)) & 
                (play_df.text.str.contains("forced by", case=False, flags=0, na=False, regex=True)),
                play_df.text.str.extract(r"forced by( .{0,25}),", flags=re.IGNORECASE).bfill(axis=1)[0],
                play_df.fumble_forced_player
            )
            play_df["fumble_forced_player"]  = play_df.fumble_forced_player.str.replace(" \((.+)\)", "", regex=True)
            play_df["fumble_forced_player"]  = play_df.fumble_forced_player.str.replace(" \(\)", "", regex=True)
            
            play_df["fumble_recovered_player"] = np.where(
                (play_df.text.str.contains("fumble", case=False, flags=0, na=False, regex=True)) & 
                (play_df.text.str.contains("recovered by", case=False, flags=0, na=False, regex=True)),
                play_df.text.str.extract(r"recovered by( .{0,30}),", flags=re.IGNORECASE).bfill(axis=1)[0],
                play_df.fumble_recovered_player
            )
            play_df["fumble_recovered_player"]  = play_df.fumble_recovered_player.str.replace(" \((.+)\)", "", regex=True)
            play_df["fumble_recovered_player"]  = play_df.fumble_recovered_player.str.replace(" \(\)", "", regex=True)
        # print(min(play_df["season"]))

        play_df["fumble_player"] = np.where(play_df["type.text"] == "Penalty", None, play_df.fumble_player)
        play_df["fumble_forced_player"] = np.where(play_df["type.text"] == "Penalty", None, play_df.fumble_forced_player)
        play_df["fumble_recovered_player"] = np.where(play_df["type.text"] == "Penalty", None, play_df.fumble_recovered_player)

        ## Extract player names - final layer, renaming
        play_df['sack_player_name'] = play_df['sack_player1'].str.strip()
        play_df['sack_player_name2'] = play_df['sack_player2'].str.strip()
        play_df['pass_breakup_player_name'] = play_df['pass_breakup_player'].str.strip()
        play_df['interception_player_name'] = play_df['interception_player'].str.strip()
        play_df['fumble_player_name'] = play_df['fumble_player'].str.strip()
        play_df['forced_fumble_player_name'] = play_df['fumble_forced_player'].str.strip()
        play_df['fumble_recovery_player_name'] = play_df['fumble_recovered_player'].str.strip()

        play_df['fg_returner_player_name'] = play_df['fg_return_player'].str.strip()
        play_df['kickoff_returner_player_name'] = play_df['kickoff_return_player'].str.strip()
        play_df['punt_returned_player_name'] = play_df['punt_return_player'].str.strip()
        play_df['punt_blocked_returner_player_name'] = play_df['punt_block_return_player'].str.strip()
        play_df['fg_kicker_player_name'] = play_df['fg_kicker_player'].str.strip()
        play_df['kickoff_player_name'] = play_df['kickoff_player'].str.strip()
        play_df['fg_blocked_player_name'] = play_df['fg_block_player'].str.strip()
        play_df['punt_blocked_player_name'] = play_df['punt_block_player'].str.strip()
        play_df['blocked_player_name'] = play_df[['fg_blocked_player_name', 'punt_blocked_player_name']].bfill(axis=1).iloc[:, 0]
        play_df['kicker_player_name'] = play_df[['fg_kicker_player_name', 'kickoff_player_name']].bfill(axis=1).iloc[:, 0]
        play_df['kick_returner_player_name'] = play_df[['kickoff_returner_player_name','fg_returner_player_name']].bfill(axis=1).iloc[:,0]
        play_df['punt_returner_player_name'] = play_df[['punt_returned_player_name','punt_blocked_returner_player_name']].bfill(axis=1).iloc[:,0]
        play_df['punter_player_name'] = play_df['punter_player'].str.strip()
        play_df['passer_player_name'] = play_df['pass_player'].str.strip()
        play_df['rusher_player_name'] = play_df['rush_player'].str.strip()
        play_df['receiver_player_name'] = play_df['receiver_player'].str.strip()

        play_df.drop([
            'rush_player',
            'receiver_player',
            'pass_player',
            'sack_player1',
            'sack_player2',
            'pass_breakup_player',
            'interception_player',
            'punter_player',
            'fg_kicker_player',
            'fg_block_player',
            'fg_return_player',
            'kickoff_player',
            'kickoff_return_player',
            'punt_return_player',
            'punt_block_player',
            'punt_block_return_player',
            'fumble_player',
            'fumble_forced_player',
            'fumble_recovered_player'
        ],axis=1, inplace=True)

        return play_df

    def after_cols(self, play_df):
        play_df['new_down'] =  np.select(
            [
                (play_df["type.text"] == "Timeout"),
                # 8 cases with three T/F penalty flags
                # 4 cases in 1
                (play_df["type.text"].isin(penalty)) & (play_df["penalty_1st_conv"]==True),
                # offsetting penalties, no penalties declined, no 1st down by penalty (1 case)
                (play_df["type.text"].isin(penalty)) & (play_df["penalty_1st_conv"]==False) &
                    (play_df["penalty_offset"]==True) & (play_df["penalty_declined"]==False),
                # offsetting penalties, penalty declined true, no 1st down by penalty
                # seems like it would be a regular play at that point (1 case, split in three)
                (play_df["type.text"].isin(penalty)) & (play_df["penalty_1st_conv"]==False) &
                    (play_df["penalty_offset"]==True) & (play_df["penalty_declined"]==True) &
                    (play_df['statYardage'] < play_df['start.ydstogo']) & (play_df['start.down']<=3),
                (play_df["type.text"].isin(penalty)) & (play_df["penalty_1st_conv"]==False) &
                    (play_df["penalty_offset"]==True) & (play_df["penalty_declined"]==True) &
                    (play_df['statYardage'] < play_df['start.ydstogo']) & (play_df['start.down']==4),
                (play_df["type.text"].isin(penalty)) & (play_df["penalty_1st_conv"]==False) &
                    (play_df["penalty_offset"]==True) & (play_df["penalty_declined"]==True) &
                    (play_df['statYardage'] >= play_df['start.ydstogo']),
                # only penalty declined true, same logic as prior (1 case, split in three)
                (play_df["type.text"].isin(penalty)) & (play_df["penalty_1st_conv"]==False) &
                    (play_df["penalty_offset"]==False) & (play_df["penalty_declined"]==True) &
                    (play_df['statYardage'] < play_df['start.ydstogo']) & (play_df['start.down']<=3),
                (play_df["type.text"].isin(penalty)) & (play_df["penalty_1st_conv"]==False) &
                    (play_df["penalty_offset"]==False) & (play_df["penalty_declined"]==True) &
                    (play_df['statYardage'] < play_df['start.ydstogo']) & (play_df['start.down']==4),
                (play_df["type.text"].isin(penalty)) & (play_df["penalty_1st_conv"]==False) &
                    (play_df["penalty_offset"]==False) & (play_df["penalty_declined"]==True) &
                    (play_df['statYardage'] >= play_df['start.ydstogo']),
            ],
            [
                play_df['start.down'],
                1,
                play_df['start.down'],
                play_df['start.down'] + 1,
                1,
                1,
                play_df['start.down'] + 1,
                1,
                1
            ], default = play_df['start.down']
        )
        play_df['new_ydstogo'] =  np.select(
            [
                (play_df["type.text"] == "Timeout"),
                # 8 cases with three T/F penalty flags
                # 4 cases in 1
                (play_df["type.text"].isin(penalty)) & (play_df["penalty_1st_conv"]==True),
                # offsetting penalties, no penalties declined, no 1st down by penalty (1 case)
                (play_df["type.text"].isin(penalty)) & (play_df["penalty_1st_conv"]==False) &
                    (play_df["penalty_offset"]==True) & (play_df["penalty_declined"]==False),
                # offsetting penalties, penalty declined true, no 1st down by penalty
                # seems like it would be a regular play at that point (1 case, split in three)
                (play_df["type.text"].isin(penalty)) & (play_df["penalty_1st_conv"]==False) &
                    (play_df["penalty_offset"]==True) & (play_df["penalty_declined"]==True) &
                    (play_df['statYardage'] < play_df['start.ydstogo']) & (play_df['start.down']<=3),
                (play_df["type.text"].isin(penalty)) & (play_df["penalty_1st_conv"]==False) &
                    (play_df["penalty_offset"]==True) & (play_df["penalty_declined"]==True) &
                    (play_df['statYardage'] < play_df['start.ydstogo']) & (play_df['start.down']==4),
                (play_df["type.text"].isin(penalty)) & (play_df["penalty_1st_conv"]==False) &
                    (play_df["penalty_offset"]==True) & (play_df["penalty_declined"]==True) &
                    (play_df['statYardage'] >= play_df['start.ydstogo']),
                # only penalty declined true, same logic as prior (1 case, split in three)
                (play_df["type.text"].isin(penalty)) & (play_df["penalty_1st_conv"]==False) &
                    (play_df["penalty_offset"]==False) & (play_df["penalty_declined"]==True) &
                    (play_df['statYardage'] < play_df['start.ydstogo']) & (play_df['start.down']<=3),
                (play_df["type.text"].isin(penalty)) & (play_df["penalty_1st_conv"]==False) &
                    (play_df["penalty_offset"]==False) & (play_df["penalty_declined"]==True) &
                    (play_df['statYardage'] < play_df['start.ydstogo']) & (play_df['start.down']==4),
                (play_df["type.text"].isin(penalty)) & (play_df["penalty_1st_conv"]==False) &
                    (play_df["penalty_offset"]==False) & (play_df["penalty_declined"]==True) &
                    (play_df['statYardage'] >= play_df['start.ydstogo']),
            ],
            [
                play_df['start.ydstogo'],
                10,
                play_df['start.ydstogo'],
                play_df['start.ydstogo'] - play_df['statYardage'],
                10,
                10,
                play_df['start.ydstogo'] - play_df['statYardage'],
                10,
                10,
            ], default = play_df['start.ydstogo']
        )

        play_df['middle_8'] =  np.where((play_df['start.game_seconds_remaining'] >= 1560) & (play_df['start.game_seconds_remaining'] <= 2040), True, False)
        play_df['rz_play'] =  np.where(play_df['start.yardline_100'] <= 20, True, False)
        play_df['scoring_opp'] =  np.where(play_df['start.yardline_100'] <= 40, True, False)
        play_df['stuffed_run'] =  np.where((play_df.rush == True) & (play_df.yds_rushed <= 0), True, False)
        play_df['stopped_run'] =  np.where((play_df.rush == True) & (play_df.yds_rushed <= 2), True, False)
        play_df['opportunity_run'] =  np.where((play_df.rush == True) & (play_df.yds_rushed >= 4), True, False)
        play_df['highlight_run'] =  np.where((play_df.rush == True) & (play_df.yds_rushed >= 8), True, False)
        play_df['short_rush_success'] = np.where(
            (play_df['start.ydstogo'] < 2) & (play_df.rush == True) & (play_df.statYardage >= play_df['start.ydstogo']), True, False
        )
        play_df['short_rush_attempt'] = np.where(
            (play_df['start.ydstogo'] < 2) & (play_df.rush == True), True, False
        )
        play_df['power_rush_success'] = np.where(
            (play_df['start.ydstogo'] < 2) & (play_df.rush == True) & (play_df.statYardage >= play_df['start.ydstogo']), True, False
        )
        play_df['power_rush_attempt'] = np.where(
            (play_df['start.ydstogo'] < 2) & (play_df.rush == True), True, False
        )
        play_df['standard_down'] = np.where(
            play_df.down_1 == True, True, np.where(
                (play_df.down_2 == True) & (play_df['start.ydstogo'] < 8), True, np.where(
                    (play_df.down_3 == True) & (play_df['start.ydstogo'] < 5), True, np.where(
                        (play_df.down_4 == True) & (play_df['start.ydstogo'] < 5), True, False 
                    )
                )
            )
        )
        play_df['passing_down'] = np.where(
            play_df.down_1 == True, False, np.where(
                (play_df.down_2 == True) & (play_df['start.ydstogo'] >= 8), True, np.where(
                    (play_df.down_3 == True) & (play_df['start.ydstogo'] >= 5), True, np.where(
                        (play_df.down_4 == True) & (play_df['start.ydstogo'] >= 5), True,  False
                    )
                )
            )
        )
        play_df['TFL'] = np.where(
            (play_df['type.text'] != 'Penalty') & (play_df.special_teams == False) & (play_df.statYardage < 0), True, False
        )
        play_df['TFL_pass'] = np.where(
            (play_df['TFL'] == True) & (play_df['pass'] == True), True, False
        )
        play_df['TFL_rush'] = np.where(
            (play_df['TFL'] == True) & (play_df['rush'] == True), True, False
        )
        play_df['havoc'] = np.where(
            (play_df['fumble_forced'] == True)|(play_df['int'] == True)|(play_df['TFL'] == True)|(play_df['pass_breakup'] == True),
            True, False
        )
        play_df['havoc_pass'] = np.where(
            (play_df['havoc'] == True) & (play_df['pass'] == True), True, False
        )
        play_df['havoc_rush'] = np.where(
            (play_df['havoc'] == True) & (play_df['rush'] == True), True, False
        )
        return play_df

    def add_spread_time(self, play_df):
        play_df['start.posteam_spread'] = np.where(
            (play_df["start.posteam.id"] == play_df["homeTeamId"]), play_df['homeTeamSpread'], -1 * play_df['homeTeamSpread']
        )
        play_df['start.elapsed_share'] = ((3600 - play_df['start.game_seconds_remaining']) / 3600).clip(0, 3600)
        play_df['start.spread_time'] = play_df['start.posteam_spread'] * np.exp(-4 * play_df['start.elapsed_share'])
        #---- prepare variables for wp_after calculations ----
        play_df['end.posteam_spread'] = np.where(
            (play_df["end.posteam.id"] == play_df["homeTeamId"]), play_df['homeTeamSpread'], -1 * play_df['homeTeamSpread']
        )
        play_df['end.elapsed_share'] = ((3600 - play_df['end.game_seconds_remaining']) / 3600).clip(0, 3600).astype(float)
        play_df['end.spread_time'] = play_df['end.posteam_spread'] * np.exp(-4 * play_df['end.elapsed_share'])
        
        play_df['start.spread_time'] = play_df['start.spread_time'].astype(float)
        play_df['end.spread_time'] = play_df['end.spread_time'].astype(float)
        return play_df

    def calculate_ep_exp_val(self, matrix):
        return matrix[:,0] * ep_class_to_score_mapping[0] + matrix[:,1] * ep_class_to_score_mapping[1] + matrix[:,2] * ep_class_to_score_mapping[2] + matrix[:,3] * ep_class_to_score_mapping[3] + matrix[:,4] * ep_class_to_score_mapping[4] + matrix[:,5] * ep_class_to_score_mapping[5] + matrix[:,6] * ep_class_to_score_mapping[6]

    def process_epa(self, play_df):
        play_df.loc[play_df["type.text"].isin(kickoff_vec), "down"] = 1
        play_df.loc[play_df["type.text"].isin(kickoff_vec), "start.down"] = 1
        play_df.loc[play_df["type.text"].isin(kickoff_vec), "down_1"] = True
        play_df.loc[play_df["type.text"].isin(kickoff_vec), "down_2"] = False
        play_df.loc[play_df["type.text"].isin(kickoff_vec), "down_3"] = False
        play_df.loc[play_df["type.text"].isin(kickoff_vec), "down_4"] = False
        play_df.loc[play_df["type.text"].isin(kickoff_vec), "ydstogo"] = 10
        play_df.loc[play_df["type.text"].isin(kickoff_vec), "start.ydstogo"] = 10
        play_df["start.yardline_100.touchback"] = 99
        play_df.loc[(play_df["type.text"].isin(kickoff_vec)) & (play_df['season'] > 2013), "start.yardline_100.touchback"] = 75
        play_df.loc[(play_df["type.text"].isin(kickoff_vec)) & (play_df['season'] <= 2013), "start.yardline_100.touchback"] = 80


        play_df['down_1'] = play_df['down_1'].fillna(0).astype(int)
        play_df['down_2'] = play_df['down_2'].fillna(0).astype(int)
        play_df['down_3'] = play_df['down_3'].fillna(0).astype(int)
        play_df['down_4'] = play_df['down_4'].fillna(0).astype(int)

        play_df['down_1_end'] = play_df['down_1_end'].fillna(0).astype(int)
        play_df['down_2_end'] = play_df['down_2_end'].fillna(0).astype(int)


        play_df['down_3_end'] = play_df['down_3_end'].fillna(0).astype(int)

        play_df['down_4_end'] = play_df['down_4_end'].fillna(0).astype(int)
        play_df['start.game_seconds_remaining'] = play_df['start.game_seconds_remaining'].astype(int)
        play_df['start.half_seconds_remaining'] = play_df['start.half_seconds_remaining'].astype(int)
        play_df['start.posteam_score_differential'] = play_df['start.posteam_score_differential'].astype(int)
        play_df['end.game_seconds_remaining'] = play_df['end.game_seconds_remaining'].astype(int)
        play_df['end.half_seconds_remaining'] = play_df['end.half_seconds_remaining'].astype(int)
        play_df['end.posteam_score_differential'] = play_df['end.posteam_score_differential'].astype(int)

        start_touchback_data = play_df[ep_start_touchback_columns]
        start_touchback_data.columns = ep_final_names
        # self.logger.info(start_data.iloc[[36]].to_json(orient="records"))

        dtest_start_touchback = xgb.DMatrix(start_touchback_data)
        EP_start_touchback_parts = ep_model.predict(dtest_start_touchback)
        EP_start_touchback = self.calculate_ep_exp_val(EP_start_touchback_parts)

        start_data = play_df[ep_start_columns]
        start_data.columns = ep_final_names
        # self.logger.info(start_data.iloc[[36]].to_json(orient="records"))

        dtest_start = xgb.DMatrix(start_data)
        EP_start_parts = ep_model.predict(dtest_start)
        EP_start = self.calculate_ep_exp_val(EP_start_parts)
        play_df.loc[play_df["end.game_seconds_remaining"] <= 0, "end.game_seconds_remaining"] = 0

        play_df.loc[play_df["end.half_seconds_remaining"] <= 0, "end.half_seconds_remaining"] = 0
        play_df.loc[play_df["end.half_seconds_remaining"] <= 0, "end.yardline_100"] = 99
        play_df.loc[play_df["end.half_seconds_remaining"] <= 0, "down_1_end"] = 1
        play_df.loc[play_df["end.half_seconds_remaining"] <= 0, "down_2_end"] = 0
        play_df.loc[play_df["end.half_seconds_remaining"] <= 0, "down_3_end"] = 0
        play_df.loc[play_df["end.half_seconds_remaining"] <= 0, "down_4_end"] = 0
        play_df.loc[play_df["end.yardline_100"] >= 100, "end.yardline_100"] = 99
        play_df.loc[play_df["end.yardline_100"] <= 0, "end.yardline_100"] = 99

        end_data = play_df[ep_end_columns]
        end_data.columns = ep_final_names
        # self.logger.info(end_data.iloc[[36]].to_json(orient="records"))
        dtest_end = xgb.DMatrix(end_data)
        EP_end_parts = ep_model.predict(dtest_end)

        EP_end = self.calculate_ep_exp_val(EP_end_parts)

        play_df["EP_start_touchback"] = EP_start_touchback
        play_df['EP_start'] = EP_start
        play_df['EP_end'] = EP_end
        kick = 'kick)'
        play_df['EP_start'] = np.where(
            play_df["type.text"].isin(['Extra Point Good','Extra Point Missed', 'Two-Point Conversion Good', 'Two-Point Conversion Missed',
                                       'Two Point Pass', 'Two Point Rush', 'Blocked PAT']),
            0.92, play_df['EP_start']
        )
        play_df.EP_end = np.select([
            # End of Half
            (play_df["type.text"].str.lower().str.contains("end of game", case=False, flags=0, na=False, regex=True)) |
            (play_df["type.text"].str.lower().str.contains("end of game", case=False, flags=0, na=False, regex=True)) |
            (play_df["type.text"].str.lower().str.contains("end of half", case=False, flags=0, na=False, regex=True)) |
            (play_df["type.text"].str.lower().str.contains("end of half", case=False, flags=0, na=False, regex=True)),
            # Safeties
            ((play_df["type.text"].isin(defense_score_vec)) &
            (play_df["text"].str.lower().str.contains('safety', case=False, regex=True))),
            # Defense TD + Successful Two-Point Conversion
            ((play_df["type.text"].isin(defense_score_vec)) &
            (play_df["text"].str.lower().str.contains('conversion', case=False, regex=False)) &
            (~play_df["text"].str.lower().str.contains('failed\s?\)', case=False, regex=True))),
            # Defense TD + Failed Two-Point Conversion
            ((play_df["type.text"].isin(defense_score_vec)) &
            (play_df["text"].str.lower().str.contains('conversion', case=False, regex=False)) &
            (play_df["text"].str.lower().str.contains('failed\s?\)', case=False, regex=True))),
            # Defense TD + Kick/PAT Missed
            ((play_df["type.text"].isin(defense_score_vec)) &
            (play_df["text"].str.contains('PAT', case=True, regex=False)) &
            (play_df["text"].str.lower().str.contains('missed\s?\)', case=False, regex=True))),
            # Defense TD + Kick/PAT Good
            ((play_df["type.text"].isin(defense_score_vec)) &
            (play_df["text"].str.lower().str.contains(kick, case=False, regex=False))),
            # Defense TD
            (play_df["type.text"].isin(defense_score_vec)),
            # Offense TD + Failed Two-Point Conversion
            ((play_df["type.text"].isin(offense_score_vec)) &
            (play_df["text"].str.lower().str.contains('conversion', case=False, regex=False)) &
            (play_df["text"].str.lower().str.contains('failed\s?\)', case=False, regex=True))),
            # Offense TD + Successful Two-Point Conversion
            ((play_df["type.text"].isin(offense_score_vec)) &
            (play_df["text"].str.lower().str.contains('conversion', case=False, regex=False)) &
            (~play_df["text"].str.lower().str.contains('failed\s?\)', case=False, regex=True))),
            # Offense Made FG
            ((play_df["type.text"].isin(offense_score_vec)) &
            (play_df["type.text"].str.lower().str.contains('field goal', case=False, flags=0, na=False, regex=True)) &
            (play_df["type.text"].str.lower().str.contains('good', case=False, flags=0, na=False, regex=True))),
            # Missed FG -- Not Needed
            # (play_df["type.text"].isin(offense_score_vec)) &
            # (play_df["type.text"].str.lower().str.contains('field goal', case=False, flags=0, na=False, regex=True)) &
            # (~play_df["type.text"].str.lower().str.contains('good', case=False, flags=0, na=False, regex=True)),
            # Offense TD + Kick/PAT Missed
            ((play_df["type.text"].isin(offense_score_vec)) &
            (~play_df['text'].str.lower().str.contains('conversion', case=False, regex=False)) &
            ((play_df['text'].str.contains('PAT', case=True, regex=False))) & 
            ((play_df['text'].str.lower().str.contains('missed\s?\)', case=False, regex=True)))),
            # Offense TD + Kick PAT Good
            ((play_df["type.text"].isin(offense_score_vec)) &
            (play_df['text'].str.lower().str.contains(kick, case=False, regex=False))),
            # Offense TD
            (play_df["type.text"].isin(offense_score_vec)),
            # Extra Point Good (pre-2014 data)
            (play_df["type.text"] == "Extra Point Good"),
            # Extra Point Missed (pre-2014 data)
            (play_df["type.text"] == "Extra Point Missed"),
            # Extra Point Blocked (pre-2014 data)
            (play_df["type.text"] == "Blocked PAT"),
            # Two-Point Good (pre-2014 data)
            (play_df["type.text"] == "Two-Point Conversion Good"),
            # Two-Point Missed (pre-2014 data)
            (play_df["type.text"] == "Two-Point Conversion Missed"),
            # Two-Point No Good (pre-2014 data)
            (((play_df["type.text"] == "Two Point Pass")|(play_df["type.text"] == "Two Point Rush")) &
            (play_df['text'].str.lower().str.contains('no good', case=False, regex=False))),
            # Two-Point Good (pre-2014 data)
            (((play_df["type.text"] == "Two Point Pass")|(play_df["type.text"] == "Two Point Rush")) &
            (~play_df['text'].str.lower().str.contains('no good', case=False, regex=False))),
            # Flips for Turnovers that aren't kickoffs
            (((play_df["type.text"].isin(end_change_vec)) | (play_df.downs_turnover == True)) & (play_df.kickoff_play==False)),
            # Flips for Turnovers that are on kickoffs
            (play_df["type.text"].isin(kickoff_turnovers))
        ],
        [
            0,
            -2,
            -6,
            -8,
            -6,
            -7,
            -6.92,
            6,
            8,
            3,
            6,
            7,
            6.92,
            1,
            0,
            0,
            2,
            0,
            0,
            2,
            (play_df.EP_end * -1),
            (play_df.EP_end * -1)
        ], default = play_df.EP_end)
        play_df['lag_EP_end'] = play_df['EP_end'].shift(1)
        play_df['lag_change_of_posteam'] = play_df.change_of_posteam.shift(1)
        play_df['lag_change_of_posteam'] = np.where(
            play_df['lag_change_of_posteam'].isna(), False, play_df['lag_change_of_posteam']
        )
        play_df['EP_between'] = np.where(
            play_df.lag_change_of_posteam == True,
            play_df['EP_start'] + play_df['lag_EP_end'],
            play_df['EP_start'] - play_df['lag_EP_end']
        )
        play_df['EP_start'] = np.where(
            (play_df["type.text"].isin(['Timeout','End Period'])) & (play_df['lag_change_of_posteam'] == False),
            play_df['lag_EP_end'],
            play_df['EP_start']
        )
        play_df['EP_start'] = np.where(
            (play_df["type.text"].isin(kickoff_vec)),
            play_df['EP_start_touchback'],
            play_df['EP_start']
        )
        play_df['EP_end'] = np.where(
            (play_df["type.text"] == "Timeout"),
            play_df['EP_start'],
            play_df['EP_end']
        )
        play_df['EPA'] = np.select(
            [
                (play_df["type.text"] == "Timeout"),
                (play_df["scoring_play"] == False) & (play_df['end_of_half'] == True),
                (play_df["type.text"].isin(kickoff_vec)) & (play_df["penalty_in_text"] == True),
                (play_df["penalty_in_text"] == True) & (play_df["type.text"] != "Penalty") & (~play_df["type.text"].isin(kickoff_vec))
            ],
            [
                0,
                -1*play_df['EP_start'],
                play_df['EP_end'] - play_df['EP_start'],
                (play_df['EP_end'] - play_df['EP_start'] + play_df['EP_between'])
            ],
            default = (play_df['EP_end'] - play_df['EP_start'])
        )
        play_df['def_EPA'] = -1*play_df['EPA']
        #----- EPA Summary flags ------
        play_df['EPA_scrimmage'] = np.select(
            [
                (play_df.scrimmage_play == True)
            ],
            [
                play_df.EPA
            ], default = None
        )
        play_df['EPA_rush'] = np.select(
            [
                (play_df.rush == True) & (play_df['penalty_in_text'] == True),
                (play_df.rush == True) & (play_df['penalty_in_text'] == False)
            ],
            [
                play_df.EPA,
                play_df.EPA
            ], default= None
        )
        play_df['EPA_pass'] = np.where((play_df['pass'] == True), play_df.EPA, None)

        play_df['EPA_explosive'] = np.where(
            ((play_df['pass'] == True) & (play_df['EPA'] >= 2.4))|
            (((play_df['rush'] == True) & (play_df['EPA'] >= 1.8))), True, False)
        play_df['EPA_explosive_pass'] = np.where(((play_df['pass'] == True) & (play_df['EPA'] >= 2.4)), True, False)
        play_df['EPA_explosive_rush'] = np.where((((play_df['rush'] == True) & (play_df['EPA'] >= 1.8))), True, False)

        play_df['EPA_success'] =  np.where(
            play_df.EPA > 0, True, False
        )
        play_df['EPA_success_standard_down'] =  np.where(
            (play_df.EPA > 0) & (play_df.standard_down == True), True, False
        )
        play_df['EPA_success_passing_down'] =  np.where(
            (play_df.EPA > 0) & (play_df.passing_down == True), True, False
        )
        play_df['EPA_success_pass'] =  np.where(
            (play_df.EPA > 0) & (play_df['pass'] == True), True, False
        )
        play_df['EPA_success_rush'] =  np.where(
            (play_df.EPA > 0) & (play_df.rush == True), True, False
        )
        play_df['EPA_success_EPA'] = np.where(
            play_df.EPA > 0, play_df.EPA, None
        )
        play_df['EPA_success_standard_down_EPA'] =  np.where(
            (play_df.EPA > 0) & (play_df.standard_down == True), play_df.EPA, None
        )
        play_df['EPA_success_passing_down_EPA'] =  np.where(
            (play_df.EPA > 0) & (play_df.passing_down == True), play_df.EPA, None
        )
        play_df['EPA_success_pass_EPA'] =  np.where(
            (play_df.EPA > 0) & (play_df['pass'] == True), play_df.EPA, None
        )
        play_df['EPA_success_rush_EPA'] =  np.where(
            (play_df.EPA > 0) & (play_df.rush == True), True, False
        )
        play_df['EPA_penalty'] = np.select(
            [
                (play_df['type.text'].isin(['Penalty','Penalty (Kickoff)'])),
                (play_df['penalty_in_text'] == True)
            ],
            [
                play_df['EPA'],
                play_df['EP_end'] - play_df['EP_start']
            ], default = None
        )
        play_df['EPA_special_teams'] = np.where(
           (play_df.field_goal_attempt == True)|(play_df.punt == True)|(play_df.kickoff_play == True), play_df['EPA'], False
        )
        play_df['EPA_fg'] = np.where(
           (play_df.field_goal_attempt == True), play_df['EPA'], None
        )
        play_df['EPA_punt'] = np.where(
           (play_df.punt == True), play_df['EPA'], None
        )
        play_df['EPA_kickoff'] = np.where(
           (play_df.kickoff_play == True), play_df['EPA'], None
        )
        return play_df

    def prepare_wpa(self, play_df):
        #---- prepare variables for wp_before calculations ----
        play_df['start.ExpScoreDiff_touchback'] = np.select(
            [
                (play_df["type.text"].isin(kickoff_vec))
            ],
            [
                play_df['start.posteam_score_differential'] + play_df['EP_start_touchback']
            ], default = 0.000
        )
        play_df['start.ExpScoreDiff'] = np.select(
            [
                (play_df["penalty_in_text"] == True) & (play_df["type.text"] != "Penalty"),
                (play_df["type.text"] == "Timeout") & (play_df["lag_scoringPlay"] == True)
            ],
            [
                play_df['start.posteam_score_differential'] + play_df['EP_start'] - play_df['EP_between'],
                (play_df["start.posteam_score_differential"] + 0.92) 
            ], default = play_df['start.posteam_score_differential'] + play_df.EP_start
        )
        play_df['start.ExpScoreDiff_Time_Ratio_touchback'] = play_df['start.ExpScoreDiff_touchback'] / (play_df['start.game_seconds_remaining'] + 1)
        play_df['start.ExpScoreDiff_Time_Ratio'] = play_df['start.ExpScoreDiff'] / (play_df['start.game_seconds_remaining'] + 1)

        play_df['end.ExpScoreDiff'] = np.select(
            [
                # Flips for Turnovers that aren't kickoffs
                (((play_df["type.text"].isin(end_change_vec)) | (play_df.downs_turnover == True)) & (play_df.kickoff_play==False) & (play_df["scoringPlay"] == False)),
                # Flips for Turnovers that are on kickoffs
                (play_df["type.text"].isin(kickoff_turnovers)) & (play_df["scoringPlay"] == False),
                (play_df["scoringPlay"] == False) & (play_df["type.text"] != "Timeout"),
                (play_df["scoringPlay"] == False) & (play_df["type.text"] == "Timeout"),
                (play_df["scoringPlay"] == True) & (play_df["td_play"] == True) &
                (play_df["type.text"].isin(defense_score_vec)) & (play_df.season <= 2013),
                (play_df["scoringPlay"] == True) & (play_df["td_play"] == True) &
                (play_df["type.text"].isin(offense_score_vec)) & (play_df.season <= 2013),
                (play_df["type.text"] == "Timeout") & (play_df["lag_scoringPlay"] == True) &
                (play_df.season <= 2013)

            ],
            [

                play_df['end.posteam_score_differential'] - play_df.EP_end,
                play_df['end.posteam_score_differential'] + play_df.EP_end,
                play_df['end.posteam_score_differential'] + play_df.EP_end,
                play_df['end.posteam_score_differential'] + play_df.EP_end,
                play_df['end.posteam_score_differential'] + 0.92,
                play_df['end.posteam_score_differential'] + 0.92,
                play_df['end.posteam_score_differential'] + 0.92
            ], default = play_df['end.posteam_score_differential']
        )
        play_df['end.ExpScoreDiff_Time_Ratio'] = play_df['end.ExpScoreDiff'] / (play_df["end.game_seconds_remaining"] + 1)

        return play_df

    def process_wpa(self, play_df):
        #---- wp_before ----
        start_touchback_data = play_df[wp_start_touchback_columns]
        start_touchback_data.columns = wp_final_names
        # self.logger.info(start_touchback_data.iloc[[36]].to_json(orient="records"))
        dtest_start_touchback = xgb.DMatrix(start_touchback_data)
        WP_start_touchback = wp_model.predict(dtest_start_touchback)
        start_data = play_df[wp_start_columns]
        start_data.columns = wp_final_names
        # self.logger.info(start_data.iloc[[36]].to_json(orient="records"))
        dtest_start = xgb.DMatrix(start_data)
        WP_start = wp_model.predict(dtest_start)
        play_df['wp_before'] = WP_start
        play_df['wp_touchback'] = WP_start_touchback
        play_df['wp_before'] = np.where(play_df['type.text'].isin(kickoff_vec), play_df['wp_touchback'], play_df['wp_before'])
        play_df['def_wp_before']  = 1 - play_df.wp_before
        play_df['home_wp_before'] = np.where(play_df['start.posteam.id'] == play_df["homeTeamId"],
                                             play_df.wp_before,
                                             play_df.def_wp_before)
        play_df['away_wp_before'] = np.where(play_df['start.posteam.id'] != play_df["homeTeamId"],
                                             play_df.wp_before,
                                             play_df.def_wp_before)
        #---- wp_after ----
        end_data = play_df[wp_end_columns]
        end_data.columns = wp_final_names
        # self.logger.info(start_data.iloc[[36]].to_json(orient="records"))
        dtest_end = xgb.DMatrix(end_data)
        WP_end = wp_model.predict(dtest_end)
        play_df['wp_after'] = WP_end
        play_df['def_wp_after']  = 1 - play_df.wp_after
        play_df['home_wp_after'] = np.where(play_df['end.posteam.id'] == play_df["homeTeamId"],
                                             play_df.wp_after,
                                             play_df.def_wp_after)
        play_df['away_wp_after'] = np.where(play_df['end.posteam.id'] != play_df["homeTeamId"],
                                            play_df.wp_after,
                                            play_df.def_wp_after)
        play_df['lead_wp_before'] = play_df['wp_before'].shift(-1)
        play_df['lead_wp_before2'] = play_df['wp_before'].shift(-2)

        # base wpa
        play_df['wpa_base'] = play_df.wp_after - play_df.wp_before
        play_df['wpa_base_nxt'] = play_df.lead_wp_before - play_df.wp_before
        play_df['wpa_base_nxt2'] = play_df.lead_wp_before2 - play_df.wp_before
        play_df['wpa_base_ind'] = (play_df['start.posteam.id'] == play_df['end.posteam.id'])
        play_df['wpa_base_nxt_ind'] = (play_df['start.posteam.id'] == play_df.lead_posteam)
        play_df['wpa_base_nxt2_ind'] = (play_df['start.posteam.id'] == play_df.lead_posteam2)

        # account for turnover
        play_df['wpa_change'] = (1 - play_df.wp_after) - play_df.wp_before
        play_df['wpa_change_nxt'] = (1 - play_df.lead_wp_before) - play_df.wp_before
        play_df['wpa_change_nxt2'] = (1 - play_df.lead_wp_before2) - play_df.wp_before
        play_df['wpa_change_ind'] = (play_df['start.posteam.id'] != play_df['end.posteam.id'])
        play_df['wpa_change_nxt_ind'] = (play_df['start.posteam.id'] != play_df.lead_posteam)
        play_df['wpa_change_nxt2_ind'] = (play_df['start.posteam.id'] != play_df.lead_posteam2)
        play_df['wpa_half_end'] = np.select(
            [
                (play_df.end_of_half == 1) & (play_df.wpa_base_nxt_ind == 1) & (play_df['type.text'] != "Timeout"),
                (play_df.end_of_half == 1) & (play_df.wpa_change_nxt_ind == 1) & (play_df['type.text'] != "Timeout"),
                (play_df.end_of_half == 1) & (play_df['start.posteam_receives_2H_kickoff'] == False) & (play_df['type.text'] == "Timeout"),
                (play_df.wpa_change_ind == 1)
            ],
            [
                play_df.wpa_base_nxt,
                play_df.wpa_change_nxt,
                play_df.wpa_base,
                play_df.wpa_change
            ], default = play_df.wpa_base
        )

        play_df['wpa'] = np.select(
            [
                (play_df.end_of_half == 1) & (play_df['type.text'] != "Timeout"),
                (play_df.lead_play_type.isin(["End Period", "End of Half"])) & (play_df.change_of_posteam == 0),
                (play_df.lead_play_type.isin(["End Period", "End of Half"])) & (play_df.change_of_posteam == 1),
                play_df.wpa_change_ind == 1
            ],
            [
                play_df.wpa_half_end,
                play_df.wpa_base_nxt,
                play_df.wpa_change_nxt,
                play_df.wpa_change
            ], default =  play_df.wpa_base
        )

        # play_df['wp_after'] = play_df.wp_before + play_df.wpa
        # play_df['def_wp_after'] = 1 - play_df.wp_after
        # play_df['home_wp_after'] = np.where(play_df['start.posteam.id'] == play_df["homeTeamId"],
        #                 play_df.home_wp_before + play_df.wpa,
        #                 play_df.home_wp_before - play_df.wpa)
        # play_df['away_wp_after'] = np.where(play_df['start.posteam.id'] != play_df["homeTeamId"],
        #                 play_df.away_wp_before + play_df.wpa,
        #                 play_df.away_wp_before - play_df.wpa)

        return play_df

    def add_drive_data(self, play_df):
        base_groups = play_df.groupby(['drive.id'])
        play_df['drive_start'] = np.where(
            play_df['start.posteam.id'] == play_df["homeTeamId"],
            100 - play_df["drive.start.yardLine"].astype(float),
            play_df["drive.start.yardLine"].astype(float)
        )
        play_df['drive_play_index'] = base_groups['scrimmage_play'].apply(lambda x: x.cumsum())
        play_df['drive_offense_plays'] = np.where((play_df['special_teams']==False) & (play_df['scrimmage_play'] == True), play_df['play'].astype(int), 0)
        play_df['prog_drive_EPA'] = base_groups['EPA_scrimmage'].apply(lambda x: x.cumsum())
        play_df['prog_drive_WPA'] = base_groups['wpa'].apply(lambda x: x.cumsum())
        play_df['drive_offense_yards'] = np.where(play_df['special_teams']==False & (play_df['scrimmage_play'] == True), play_df['statYardage'], 0)
        play_df['drive_total_yards'] = play_df.groupby(['drive.id'])['drive_offense_yards'].apply(lambda x: x.cumsum())
        return play_df

    def create_box_score(self):
        if ((self.ran_clean_pipeline == False) & (len(self.plays_json.index)>0)):
            self.run_processing_pipeline()
        if (len(self.plays_json.index)>0):

            # have to run the pipeline before pulling this in
            self.plays_json['complete_pass'] = self.plays_json['complete_pass'].astype(float)
            self.plays_json['pass_attempt'] = self.plays_json['pass_attempt'].astype(float)
            self.plays_json['target'] = self.plays_json['target'].astype(float)
            self.plays_json['yds_receiving'] = self.plays_json['yds_receiving'].astype(float)
            self.plays_json['yds_rushed'] = self.plays_json['yds_rushed'].astype(float)
            self.plays_json['rush'] = self.plays_json['rush'].astype(float)
            self.plays_json['rush_touchdown'] = self.plays_json['rush_touchdown'].astype(float)
            self.plays_json['pass'] = self.plays_json['pass'].astype(float)
            self.plays_json['pass_touchdown'] = self.plays_json['pass_touchdown'].astype(float)
            self.plays_json['EPA'] = self.plays_json['EPA'].astype(float)
            self.plays_json['wpa'] = self.plays_json['wpa'].astype(float)
            self.plays_json['int'] = self.plays_json['int'].astype(float)
            self.plays_json['int_td'] = self.plays_json['int_td'].astype(float)
            self.plays_json['def_EPA'] = self.plays_json['def_EPA'].astype(float)
            self.plays_json['EPA_rush'] = self.plays_json['EPA_rush'].astype(float)
            self.plays_json['EPA_pass'] = self.plays_json['EPA_pass'].astype(float)
            self.plays_json['EPA_success'] = self.plays_json['EPA_success'].astype(float)
            self.plays_json['EPA_success_pass'] = self.plays_json['EPA_success_pass'].astype(float)
            self.plays_json['EPA_success_rush'] = self.plays_json['EPA_success_rush'].astype(float)
            self.plays_json['EPA_success_standard_down'] = self.plays_json['EPA_success_standard_down'].astype(float)
            self.plays_json['EPA_success_passing_down'] = self.plays_json['EPA_success_passing_down'].astype(float)
            self.plays_json['middle_8'] = self.plays_json['middle_8'].astype(float)
            self.plays_json['rz_play'] = self.plays_json['rz_play'].astype(float)
            self.plays_json['scoring_opp'] = self.plays_json['scoring_opp'].astype(float)
            self.plays_json['stuffed_run'] = self.plays_json['stuffed_run'].astype(float)
            self.plays_json['stopped_run'] = self.plays_json['stopped_run'].astype(float)
            self.plays_json['opportunity_run'] = self.plays_json['opportunity_run'].astype(float)
            self.plays_json['highlight_run'] =  self.plays_json['highlight_run'].astype(float)
            self.plays_json['short_rush_success'] = self.plays_json['short_rush_success'].astype(float)
            self.plays_json['short_rush_attempt'] = self.plays_json['short_rush_attempt'].astype(float)
            self.plays_json['power_rush_success'] = self.plays_json['power_rush_success'].astype(float)
            self.plays_json['power_rush_attempt'] = self.plays_json['power_rush_attempt'].astype(float)
            self.plays_json['EPA_explosive'] = self.plays_json['EPA_explosive'].astype(float)
            self.plays_json['EPA_explosive_pass'] = self.plays_json['EPA_explosive_pass'].astype(float)
            self.plays_json['EPA_explosive_rush'] = self.plays_json['EPA_explosive_rush'].astype(float)
            self.plays_json['standard_down'] = self.plays_json['standard_down'].astype(float)
            self.plays_json['passing_down'] = self.plays_json['passing_down'].astype(float)
            self.plays_json['fumble'] = self.plays_json['fumble'].astype(float)
            self.plays_json['sack'] = self.plays_json['sack'].astype(float)
            self.plays_json['penalty_flag'] = self.plays_json['penalty_flag'].astype(float)
            self.plays_json['play'] = self.plays_json['play'].astype(float)
            self.plays_json['scrimmage_play'] = self.plays_json['scrimmage_play'].astype(float)
            self.plays_json['special_teams'] = self.plays_json['special_teams'].astype(float)
            self.plays_json['kickoff_play'] = self.plays_json['kickoff_play'].astype(float)
            self.plays_json['punt'] = self.plays_json['punt'].astype(float)
            self.plays_json['field_goal_attempt'] = self.plays_json['field_goal_attempt'].astype(float)
            self.plays_json['EPA_penalty'] = self.plays_json['EPA_penalty'].astype(float)
            self.plays_json['EPA_special_teams'] = self.plays_json['EPA_special_teams'].astype(float)
            self.plays_json['EPA_fg'] = self.plays_json['EPA_fg'].astype(float)
            self.plays_json['EPA_punt'] = self.plays_json['EPA_punt'].astype(float)
            self.plays_json['EPA_kickoff'] = self.plays_json['EPA_kickoff'].astype(float)
            self.plays_json['TFL'] = self.plays_json['TFL'].astype(float)
            self.plays_json['TFL_pass'] = self.plays_json['TFL_pass'].astype(float)
            self.plays_json['TFL_rush'] = self.plays_json['TFL_rush'].astype(float)
            self.plays_json['havoc'] = self.plays_json['havoc'].astype(float)
            self.plays_json['havoc_pass'] = self.plays_json['havoc_pass'].astype(float)
            self.plays_json['havoc_rush'] = self.plays_json['havoc_rush'].astype(float)

            pass_box = self.plays_json[self.plays_json["pass"] == 1]
            rush_box = self.plays_json[self.plays_json.rush == 1]

            passer_box = pass_box.groupby(by=["posteam","passer_player_name"], as_index=False).agg(
                Comp = ('complete_pass', sum),
                Att = ('pass_attempt',sum),
                Yds = ('yds_receiving',sum),
                Pass_TD = ('pass_touchdown', sum),
                Int = ('int', sum),
                YPA = ('yds_receiving', mean),
                EPA = ('EPA', sum),
                EPA_per_Play = ('EPA', mean),
                WPA = ('wpa', sum),
                SR = ('EPA_success', mean)
            ).round(2)
            passer_box = passer_box.replace({np.nan: None})

            rusher_box = rush_box.groupby(by=["posteam","rusher_player_name"], as_index=False).agg(
                Car= ('rush', sum),
                Yds= ('yds_rushed',sum),
                Rush_TD = ('rush_touchdown',sum),
                YPC= ('yds_rushed', mean),
                EPA= ('EPA', sum),
                EPA_per_Play= ('EPA', mean),
                WPA= ('wpa', sum),
                SR = ('EPA_success', mean)
            ).round(2)
            rusher_box = rusher_box.replace({np.nan: None})

            receiver_box = pass_box.groupby(by=["posteam","receiver_player_name"], as_index=False).agg(
                Rec= ('complete_pass', sum),
                Tar= ('target',sum),
                Yds= ('yds_receiving',sum),
                Rec_TD = ('pass_touchdown', sum),
                YPT= ('yds_receiving', mean),
                EPA= ('EPA', sum),
                EPA_per_Play= ('EPA', mean),
                WPA= ('wpa', sum),
                SR = ('EPA_success', mean)
            ).round(2)
            receiver_box = receiver_box.replace({np.nan: None})

            team_box = self.plays_json.groupby(by=["posteam"], as_index=False).agg(
                EPA_plays = ('play', sum),
                scrimmage_plays = ('scrimmage_play', sum),
                EPA_overall_total = ('EPA', sum),
                EPA_passing_overall = ('EPA_pass', sum),
                EPA_rushing_overall = ('EPA_rush', sum),
                EPA_per_play = ('EPA', mean),
                EPA_passing_per_play = ('EPA_pass', mean),
                EPA_rushing_per_play = ('EPA_rush', mean),
                rushes = ('rush', sum),
                rushing_power_success= ('power_rush_success', sum),
                rushing_power_attempt= ('power_rush_attempt', sum),
                rushing_stuff_rate = ('stuffed_run', sum),
                rushing_stopped_rate = ('stopped_run', sum),
                rushing_opportunity_rate = ('opportunity_run', sum),
                rushing_highlight_run = ('highlight_run', sum),
                passes = ('pass', sum),
                passes_completed = ('complete_pass', sum),
                passes_attempted = ('pass_attempt', sum),
                EPA_explosive = ('EPA_explosive', sum),
                EPA_explosive_passing = ('EPA_explosive_pass', sum),
                EPA_explosive_rushing = ('EPA_explosive_rush', sum),
                EPA_success = ('EPA_success', sum),
                EPA_success_pass = ('EPA_success_pass', sum),
                EPA_success_rush = ('EPA_success_rush', sum),
                EPA_success_standard_down = ('EPA_success_standard_down', sum),
                EPA_success_passing_down = ('EPA_success_passing_down', sum),
                EPA_penalty = ('EPA_penalty', sum),
                special_teams_plays = ('special_teams', sum),
                EPA_special_teams = ('EPA_special_teams', sum),
                EPA_fg = ('EPA_fg', sum),
                EPA_punt = ('EPA_punt', sum),
                kickoff_plays = ('kickoff_play', sum),
                EPA_kickoff = ('EPA_kickoff', sum),
                TFL = ('TFL', sum),
                TFL_pass = ('TFL_pass', sum),
                TFL_rush = ('TFL_rush', sum),
                havoc_total = ('havoc', sum),
                havoc_total_pass = ('havoc_pass', sum),
                havoc_total_rush = ('havoc_rush', sum)
            ).round(2)

            team_box = team_box.replace({np.nan:None})

            return {
                "pass" : json.loads(passer_box.to_json(orient="records")),
                "rush" : json.loads(rusher_box.to_json(orient="records")),
                "receiver" : json.loads(receiver_box.to_json(orient="records")),
                "team" : json.loads(team_box.to_json(orient="records"))
            }
        else:
            return

    def process():
        gameId = request.get_json(force=True)['gameId']
        processed_data = PlayProcess( gameId = gameId)
        pbp = processed_data.cfb_pbp()
        processed_data.run_processing_pipeline()
        tmp_json = processed_data.plays_json.to_json(orient="records")
        jsonified_df = json.loads(tmp_json)

        box = processed_data.create_box_score()
        bad_cols = [
            'start.distance', 'start.yardLine', 'start.team.id', 'start.down', 'start.yardsToEndzone', 'start.posteamTimeouts', 'start.defTeamTimeouts', 
            'start.shortDownDistanceText', 'start.possessionText', 'start.downDistanceText', 'start.pos_team_timeouts', 'start.def_pos_team_timeouts',
            'clock.displayValue',
            'type.id', 'type.text', 'type.abbreviation',
            'end.distance', 'end.yardLine', 'end.team.id','end.down', 'end.yardsToEndzone', 'end.posteamTimeouts','end.defTeamTimeouts', 
            'end.shortDownDistanceText', 'end.possessionText', 'end.downDistanceText', 'end.pos_team_timeouts', 'end.def_pos_team_timeouts',
            'expectedPoints.before', 'expectedPoints.after', 'expectedPoints.added', 
            'winProbability.before', 'winProbability.after', 'winProbability.added', 
            'scoringType.displayName', 'scoringType.name', 'scoringType.abbreviation'
        ]
        # clean records back into ESPN format
        for record in jsonified_df:
            record["clock"] = {
                "displayValue" : record["clock.displayValue"]
            }

            record["type"] = {
                "id" : record["type.id"],
                "text" : record["type.text"],
                "abbreviation" : record["type.abbreviation"],
            }
            record["modelInputs"] = {
                "start" : {
                    "down" : record["start.down"],
                    "distance" : record["start.distance"],
                    "yardsToEndzone" : record["start.yardsToEndzone"],
                    "TimeSecsRem": record["start.TimeSecsRem"],
                    "adj_TimeSecsRem" : record["start.adj_TimeSecsRem"],
                    "pos_score_diff" : record["start.pos_score_diff"],
                    "posteamTimeouts" : record["start.posteamTimeouts"],
                    "defTeamTimeouts" : record["start.defteamTimeouts"],
                    "ExpScoreDiff" : record["start.ExpScoreDiff"],
                    "ExpScoreDiff_Time_Ratio" : record["start.ExpScoreDiff_Time_Ratio"],
                    "spread_time" : record['start.spread_time'],
                    "pos_team_receives_2H_kickoff": record["start.pos_team_receives_2H_kickoff"],
                    "is_home": record["start.is_home"],
                    "period": record["period"]
                },
                "end" : {
                    "down" : record["end.down"],
                    "distance" : record["end.distance"],
                    "yardsToEndzone" : record["end.yardsToEndzone"],
                    "TimeSecsRem": record["end.TimeSecsRem"],
                    "adj_TimeSecsRem" : record["end.adj_TimeSecsRem"],
                    "posteamTimeouts" : record["end.posteamTimeouts"],
                    "defTeamTimeouts" : record["end.defteamTimeouts"],
                    "pos_score_diff" : record["end.pos_score_diff"],
                    "ExpScoreDiff" : record["end.ExpScoreDiff"],
                    "ExpScoreDiff_Time_Ratio" : record["end.ExpScoreDiff_Time_Ratio"],
                    "spread_time" : record['end.spread_time'],
                    "pos_team_receives_2H_kickoff": record["end.pos_team_receives_2H_kickoff"],
                    "is_home": record["end.is_home"],
                    "period": record["period"]
                }
            }

            record["expectedPoints"] = {
                "before" : record["EP_start"],
                "after" : record["EP_end"],
                "added" : record["EPA"]
            }

            record["winProbability"] = {
                "before" : record["wp_before"],
                "after" : record["wp_after"],
                "added" : record["wpa"]
            }

            record["start"] = {
                "team" : {
                    "id" : record["start.team.id"],
                },
                "pos_team": {
                    "id" : record["start.pos_team.id"],
                    "name" : record["start.pos_team.name"]
                },
                "def_pos_team": {
                    "id" : record["start.def_pos_team.id"],
                    "name" : record["start.def_pos_team.name"],
                },
                "distance" : record["start.distance"],
                "yardLine" : record["start.yardLine"],
                "down" : record["start.down"],
                "yardsToEndzone" : record["start.yardsToEndzone"],
                "homeScore" : record["start.homeScore"],
                "awayScore" : record["start.awayScore"],
                "pos_team_score" : record["start.pos_team_score"],
                "def_pos_team_score" : record["start.def_pos_team_score"],
                "pos_score_diff" : record["start.pos_score_diff"],
                "posteamTimeouts" : record["start.posteamTimeouts"],
                "defTeamTimeouts" : record["start.defteamTimeouts"],
                "ExpScoreDiff" : record["start.ExpScoreDiff"],
                "ExpScoreDiff_Time_Ratio" : record["start.ExpScoreDiff_Time_Ratio"],
                "shortDownDistanceText" : record["start.shortDownDistanceText"],
                "possessionText" : record["start.possessionText"],
                "downDistanceText" : record["start.downDistanceText"]
            }

            record["end"] = {
                "team" : {
                    "id" : record["end.team.id"],
                },
                "pos_team": {
                    "id" : record["end.pos_team.id"],
                    "name" : record["end.pos_team.name"],
                }, 
                "def_pos_team": {
                    "id" : record["end.def_pos_team.id"],
                    "name" : record["end.def_pos_team.name"],
                }, 
                "distance" : record["end.distance"],
                "yardLine" : record["end.yardLine"],
                "down" : record["end.down"],
                "yardsToEndzone" : record["end.yardsToEndzone"],
                "homeScore" : record["end.homeScore"],
                "awayScore" : record["end.awayScore"],
                "pos_team_score" : record["end.pos_team_score"],
                "def_pos_team_score" : record["end.def_pos_team_score"],
                "pos_score_diff" : record["end.pos_score_diff"],
                "posteamTimeouts" : record["end.posteamTimeouts"],
                "defteamTimeouts" : record["end.defteamTimeouts"],
                "ExpScoreDiff" : record["end.ExpScoreDiff"],
                "ExpScoreDiff_Time_Ratio" : record["end.ExpScoreDiff_Time_Ratio"],
                "shortDownDistanceText" : record["end.shortDownDistanceText"],
                "possessionText" : record["end.possessionText"],
                "downDistanceText" : record["end.downDistanceText"]
            }

            record["players"] = {
                'passer_player_name' : record["passer_player_name"],
                'rusher_player_name' : record["rusher_player_name"],
                'receiver_player_name' : record["receiver_player_name"],
                'sack_player_name' : record["sack_player_name"],
                'sack_player_name2' : record["sack_player_name2"],
                'pass_breakup_player_name' : record["pass_breakup_player_name"],
                'interception_player_name' : record["interception_player_name"],
                'fg_kicker_player_name' : record["fg_kicker_player_name"],
                'fg_block_player_name' : record["fg_block_player_name"],
                'fg_return_player_name' : record["fg_return_player_name"],
                'kickoff_player_name' : record["kickoff_player_name"],
                'kickoff_return_player_name' : record["kickoff_return_player_name"],
                'punter_player_name' : record["punter_player_name"],
                'punt_block_player_name' : record["punt_block_player_name"],
                'punt_return_player_name' : record["punt_return_player_name"],
                'punt_block_return_player_name' : record["punt_block_return_player_name"],
                'fumble_player_name' : record["fumble_player_name"],
                'fumble_forced_player_name' : record["fumble_forced_player_name"],
                'fumble_recovered_player_name' : record["fumble_recovered_player_name"],
            }
            # remove added columns
            for col in bad_cols:
                record.pop(col, None)

        result = {
            "id": gameId,
            "count" : len(jsonified_df),
            "plays" : jsonified_df,
            "box_score" : box,
            "homeTeamId": pbp['header']['competitions'][0]['competitors'][0]['team']['id'],
            "awayTeamId": pbp['header']['competitions'][0]['competitors'][1]['team']['id'],
            "drives" : pbp['drives'],
            "scoringPlays" : np.array(pbp['scoringPlays']).tolist(),
            "winprobability" : np.array(pbp['winprobability']).tolist(),
            "boxScore" : pbp['boxscore'],
            "homeTeamSpread" : np.array(pbp['homeTeamSpread']).tolist(),
            "header" : pbp['header'],
            "broadcasts" : np.array(pbp['broadcasts']).tolist(),
            "videos" : np.array(pbp['videos']).tolist(),
            "standings" : pbp['standings'],
            "pickcenter" : np.array(pbp['pickcenter']).tolist(),
            "espnWinProbability" : np.array(pbp['espnWP']).tolist(),
            "gameInfo" : np.array(pbp['gameInfo']).tolist(),
            "season" : np.array(pbp['season']).tolist()
        }
        # logging.getLogger("root").info(result)
        return jsonify(result)

    def run_processing_pipeline(self):
        if ((self.ran_clean_pipeline == False) & (len(self.plays_json.index)>0)):
            self.plays_json = self.add_downs_data(self.plays_json)
            self.plays_json = self.add_play_type_flags(self.plays_json)
            self.plays_json = self.add_rush_pass_flags(self.plays_json)
            self.plays_json = self.add_team_score_variables(self.plays_json)
            self.plays_json = self.add_new_play_types(self.plays_json)
            self.plays_json = self.setup_penalty_data(self.plays_json)
            self.plays_json = self.add_play_category_flags(self.plays_json)
            self.plays_json = self.add_yardage_cols(self.plays_json)
            self.plays_json = self.add_player_cols(self.plays_json)
            self.plays_json = self.after_cols(self.plays_json)
            self.plays_json = self.add_spread_time(self.plays_json)
            self.plays_json = self.process_epa(self.plays_json)
            self.plays_json = self.prepare_wpa(self.plays_json)
            self.plays_json = self.process_wpa(self.plays_json)
            self.plays_json = self.add_drive_data(self.plays_json)
            self.plays_json = self.plays_json.replace({np.nan: None})
            self.ran_clean_pipeline = True
        return self.plays_json

    def run_EP_pipeline(self):
        if ((self.ran_EP_pipeline == False) & (len(self.plays_json.index)>0)):
            self.plays_json = self.add_downs_data(self.plays_json)
            self.plays_json = self.add_play_type_flags(self.plays_json)
            self.plays_json = self.add_rush_pass_flags(self.plays_json)
            self.plays_json = self.add_team_score_variables(self.plays_json)
            self.plays_json = self.add_new_play_types(self.plays_json)
            self.plays_json = self.setup_penalty_data(self.plays_json)
            self.plays_json = self.add_play_category_flags(self.plays_json)
            self.plays_json = self.add_yardage_cols(self.plays_json)
            self.plays_json = self.add_player_cols(self.plays_json)
            self.plays_json = self.after_cols(self.plays_json)
            self.plays_json = self.add_spread_time(self.plays_json)
            self.plays_json = self.process_epa(self.plays_json)
            self.plays_json = self.prepare_wpa(self.plays_json)
            self.plays_json = self.prepare_wpa(self.plays_json)
            self.ran_EP_pipeline = True
        return self.plays_json


    def run_cleaning_pipeline(self):
        if ((self.ran_clean_pipeline == False) & (len(self.plays_json.index)>0)):
            self.plays_json = self.add_downs_data(self.plays_json)
            self.plays_json = self.add_play_type_flags(self.plays_json)
            self.plays_json = self.add_rush_pass_flags(self.plays_json)
            self.plays_json = self.add_team_score_variables(self.plays_json)
            self.plays_json = self.add_new_play_types(self.plays_json)
            self.plays_json = self.add_play_category_flags(self.plays_json)
            self.plays_json = self.add_yardage_cols(self.plays_json)
            self.plays_json = self.add_player_cols(self.plays_json)
            self.plays_json = self.after_cols(self.plays_json)
            self.plays_json = self.add_spread_time(self.plays_json)
            self.ran_clean_pipeline = True
        return self.plays_json
