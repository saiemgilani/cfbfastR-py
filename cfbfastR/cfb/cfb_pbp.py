from numpy.core.fromnumeric import mean
from flask import jsonify
import pandas as pd
import numpy as np
import xgboost as xgb
import re
import urllib
from urllib.error import URLError, HTTPError, ContentTooShortError
import json
import time
from functools import reduce, partial
from .model_vars import *
import pkg_resources

# "td" : float(p[0]),
# "opp_td" : float(p[1]),
# "fg" : float(p[2]),
# "opp_fg" : float(p[3]),
# "safety" : float(p[4]),
# "opp_safety" : float(p[5]),
# "no_score" : float(p[6])
ep_model_file = pkg_resources.resource_filename('cfbfastR', 'cfb/models/ep_model.model')
wp_spread_file = pkg_resources.resource_filename('cfbfastR', 'cfb/models/wp_spread.model')
qbr_model_file = pkg_resources.resource_filename('cfbfastR', 'cfb/models/qbr_model.model')

ep_model = xgb.Booster({'nthread': 4})  # init model
ep_model.load_model(ep_model_file)

wp_model = xgb.Booster({'nthread': 4})  # init model
wp_model.load_model(wp_spread_file)

qbr_model = xgb.Booster({'nthread': 4})  # init model
qbr_model.load_model(qbr_model_file)

    #---------------------------------
class PlayProcess(object):

    gameId = 0
    # logger = None
    ran_pipeline = False

    def __init__(self, gameId = 0):
        self.gameId = int(gameId)
        # self.logger = logger
        self.ran_pipeline = False

    def download(self, url, num_retries=5): 
        #print('Downloading:', url)
        try:
            html = urllib.request.urlopen(url).read()
        except (URLError, HTTPError, ContentTooShortError) as e: 
            print('Download error:', e.reason,url)
            html = None 
            if num_retries > 0: 
                if hasattr(e, 'code') and 500 <= e.code < 600: 
                    # recursively retry 5xx HTTP errors 
                    return self.download(url, num_retries - 1) 
        return html

    def cfb_pbp(self):
        """cfb_pbp()
        Pull the game by id
        Data from API endpoints:
        * college-football/playbyplay
        * college-football/summary
        """

        cache_buster = int(time.time() * 1000)
        # play by play
        pbp_url = f"http://cdn.espn.com/core/college-football/playbyplay?gameId={self.gameId}&xhr=1&render=false&userab=18&{cache_buster}"
        pbp_resp = self.download(url=pbp_url)
        pbp_txt = {}
        pbp_txt['scoringPlays'] = np.array([])
        pbp_txt['winprobability'] = np.array([])
        pbp_txt['standings'] = np.array([])
        pbp_txt['videos'] = np.array([])
        pbp_txt['broadcasts'] = np.array([])
        pbp_txt['pickcenter'] = np.array([])
        pbp_txt['espnWP'] = np.array([])
        pbp_txt['gameInfo'] = np.array([])
        pbp_txt['season'] = np.array([])

        pbp_txt = json.loads(pbp_resp)['gamepackageJSON']

        pbp_txt['timeouts'] = {}
        # summary endpoint for pickcenter array
        summary_url = f"http://site.api.espn.com/apis/site/v2/sports/football/college-football/summary?event={self.gameId}&{cache_buster}"
        summary_resp = self.download(summary_url)
        summary = json.loads(summary_resp)
        summary_txt = summary['pickcenter']
        # ESPN's win probability
        wp = "winprobability"
        if wp in summary:
            espnWP = summary["winprobability"]
        else:
            espnWP = np.array([])

        if 'news' in pbp_txt.keys():
            del pbp_txt['news']
        if 'shop' in pbp_txt.keys():
            del pbp_txt['shop']
        pbp_txt['gameInfo'] = pbp_txt['header']['competitions'][0]
        pbp_txt['season'] = pbp_txt['header']['season']
        pbp_txt['pickcenter'] = summary_txt
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

        pbp_txt['plays'] = pd.DataFrame()
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
        if len(pbp_txt['espnWP']) > 1:
            pbp_txt['espnWP'] = espnWP
        else:
            pbp_txt['espnWP'] = espnWP
        # Spread definition
        pbp_txt['plays']["homeTeamSpread"] = 2.5
        if len(pbp_txt['pickcenter']) > 1:
            homeFavorite = pbp_txt['pickcenter'][0]['homeTeamOdds']['favorite']
            if 'spread' in pbp_txt['pickcenter'][1].keys():
                gameSpread =  pbp_txt['pickcenter'][1]['spread']
                overUnder =  pbp_txt['pickcenter'][1]['overUnder']
            else:
                gameSpread =  pbp_txt['pickcenter'][0]['spread']
                overUnder =  pbp_txt['pickcenter'][0]['overUnder']
            # self.logger.info(f"Spread: {gameSpread}, home Favorite: {homeFavorite}, ou: {overUnder}")
        else:
            gameSpread = 2.5
            overUnder = 55.5
            homeFavorite = True

        pbp_txt['plays']["gameSpread"] = abs(gameSpread)
        pbp_txt['plays']["overUnder"] = float(overUnder)
        pbp_txt['plays']["homeTeamSpread"] = np.where(homeFavorite == True, abs(gameSpread), -1*abs(gameSpread))
        pbp_txt['homeTeamSpread'] = np.where(homeFavorite == True, abs(gameSpread), -1*abs(gameSpread))
        pbp_txt['overUnder'] = float(overUnder)
        pbp_txt['plays']["homeFavorite"] = homeFavorite
        pbp_txt['plays']["gameSpread"] = gameSpread
        pbp_txt['plays']["homeFavorite"] = homeFavorite
        # negotiating the drive meta keys into columns after unnesting drive plays
        # concatenating the previous and current drives categories when necessary
        if 'drives' in pbp_txt.keys():
            pbp_txt['plays']= pd.DataFrame()
            for key in pbp_txt['drives'].keys():
                prev_drives = pd.json_normalize(
                    data = pbp_txt['drives'][key],
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
                pbp_txt['plays'] = pd.concat([pbp_txt['plays'], prev_drives], ignore_index=True)

            pbp_txt['plays'] = pbp_txt['plays'].to_dict(orient='records')
            pbp_txt['plays'] = pd.DataFrame(pbp_txt['plays'])
            pbp_txt['plays']['season'] = pbp_txt['header']['season']['year']
            pbp_txt['plays']['seasonType'] = pbp_txt['header']['season']['type']
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
            pbp_txt['plays']["homeTeamSpread"] = 2.5
            if len(pbp_txt['pickcenter']) > 1:
                homeFavorite = pbp_txt['pickcenter'][0]['homeTeamOdds']['favorite']
                if 'spread' in pbp_txt['pickcenter'][1].keys():
                    gameSpread =  pbp_txt['pickcenter'][1]['spread']
                    overUnder =  pbp_txt['pickcenter'][1]['overUnder']
                else:
                    gameSpread =  pbp_txt['pickcenter'][0]['spread']
                    overUnder =  pbp_txt['pickcenter'][0]['overUnder']
                # self.logger.info(f"Spread: {gameSpread}, home Favorite: {homeFavorite}, ou: {overUnder}")
            else:
                gameSpread = 2.5
                overUnder = 55.5
                homeFavorite = True

            pbp_txt['plays']["gameSpread"] = abs(gameSpread)
            pbp_txt['plays']["overUnder"] = float(overUnder)
            pbp_txt['plays']["homeTeamSpread"] = np.where(homeFavorite == True, abs(gameSpread), -1*abs(gameSpread))
            pbp_txt['homeTeamSpread'] = np.where(homeFavorite == True, abs(gameSpread), -1*abs(gameSpread))
            pbp_txt['overUnder'] = float(overUnder)
            pbp_txt['plays']["homeFavorite"] = homeFavorite
            pbp_txt['plays']["gameSpread"] = gameSpread
            pbp_txt['plays']["homeFavorite"] = homeFavorite

            #----- Figuring out Timeouts ---------
            pbp_txt['timeouts'] = {}
            pbp_txt['timeouts'][homeTeamId] = {"1": [], "2": []}
            pbp_txt['timeouts'][awayTeamId] = {"1": [], "2": []}

            #----- Time ---------------
            pbp_txt['plays']['clock.mm'] = pbp_txt['plays']['clock.displayValue'].str.split(pat=':')
            pbp_txt['plays'][['clock.minutes','clock.seconds']] = pbp_txt['plays']['clock.mm'].to_list()
            pbp_txt['plays']['half'] = np.where(pbp_txt['plays']['period.number'] <= 2, "1","2")
            pbp_txt['plays']['lag_half'] = pbp_txt['plays']['half'].shift(1)
            pbp_txt['plays']['lead_half'] = pbp_txt['plays']['half'].shift(-1)
            pbp_txt['plays']['start.TimeSecsRem'] = np.where(
                pbp_txt['plays']['period.number'].isin([1,3]),
                900 + 60*pbp_txt['plays']['clock.minutes'].astype(int) + pbp_txt['plays']['clock.seconds'].astype(int),
                60*pbp_txt['plays']['clock.minutes'].astype(int) + pbp_txt['plays']['clock.seconds'].astype(int)
            )
            pbp_txt['plays']['start.adj_TimeSecsRem'] = np.select(
                [
                    pbp_txt['plays']['period.number'] == 1,
                    pbp_txt['plays']['period.number'] == 2,
                    pbp_txt['plays']['period.number'] == 3,
                    pbp_txt['plays']['period.number'] == 4
                ],
                [
                    2700 + 60*pbp_txt['plays']['clock.minutes'].astype(int)+pbp_txt['plays']['clock.seconds'].astype(int),
                    1800 + 60*pbp_txt['plays']['clock.minutes'].astype(int)+pbp_txt['plays']['clock.seconds'].astype(int),
                    900 + 60*pbp_txt['plays']['clock.minutes'].astype(int)+pbp_txt['plays']['clock.seconds'].astype(int),
                    60*pbp_txt['plays']['clock.minutes'].astype(int)+pbp_txt['plays']['clock.seconds'].astype(int)
                ], default = 60*pbp_txt['plays']['clock.minutes'].astype(int) + pbp_txt['plays']['clock.seconds'].astype(int)
            )
            # Pos Team - Start and End Id
            pbp_txt['plays']['id'] = pbp_txt['plays']['id'].apply(lambda x: int(x))
            pbp_txt['plays'] = pbp_txt['plays'].sort_values(by=["id", "start.adj_TimeSecsRem"])
            pbp_txt['plays']['game_play_number'] = np.arange(len(pbp_txt['plays']))+1
            pbp_txt['plays']['text'] = pbp_txt['plays']['text'].astype(str)
            pbp_txt['plays']["start.team.id"] = pbp_txt['plays']["start.team.id"].fillna(method='ffill').apply(lambda x: int(x))
            pbp_txt['plays']["end.team.id"] = pbp_txt['plays']["end.team.id"].fillna(value=pbp_txt['plays']["start.team.id"]).apply(lambda x: int(x))
            pbp_txt['plays']['start.pos_team.id'] = np.select(
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
            pbp_txt['plays']['start.def_pos_team.id'] = np.where(
                pbp_txt['plays']['start.pos_team.id'].astype(int) == pbp_txt['plays']['homeTeamId'].astype(int),
                pbp_txt['plays']['awayTeamId'].astype(int), pbp_txt['plays']['homeTeamId'].astype(int)
            )
            pbp_txt['plays']["end.def_team.id"] = np.where(
                pbp_txt['plays']["end.team.id"].astype(int) == pbp_txt['plays']['homeTeamId'].astype(int),
                pbp_txt['plays']['awayTeamId'].astype(int), pbp_txt['plays']['homeTeamId'].astype(int)
            )
            pbp_txt['plays']['end.pos_team.id'] = pbp_txt['plays']['end.team.id'].apply(lambda x: int(x))
            pbp_txt['plays']['end.def_pos_team.id'] = pbp_txt['plays']['end.def_team.id'].apply(lambda x: int(x))
            pbp_txt['plays']['start.pos_team.name'] = np.where(
                pbp_txt['plays']['start.pos_team.id'].astype(int) == pbp_txt['plays']['homeTeamId'].astype(int),
                pbp_txt['plays']['homeTeamName'],pbp_txt['plays']['awayTeamName']
            )
            pbp_txt['plays']['start.def_pos_team.name'] = np.where(
                pbp_txt['plays']['start.pos_team.id'].astype(int) == pbp_txt['plays']['homeTeamId'].astype(int),
                pbp_txt['plays']['awayTeamName'], pbp_txt['plays']['homeTeamName']
            )
            pbp_txt['plays']['end.pos_team.name'] = np.where(
                pbp_txt['plays']['end.pos_team.id'].astype(int) == pbp_txt['plays']['homeTeamId'].astype(int),
                pbp_txt['plays']['homeTeamName'],pbp_txt['plays']['awayTeamName']
            )
            pbp_txt['plays']['end.def_pos_team.name'] = np.where(
                pbp_txt['plays']['end.pos_team.id'].astype(int) == pbp_txt['plays']['homeTeamId'].astype(int),
                pbp_txt['plays']['awayTeamName'], pbp_txt['plays']['homeTeamName']
            )
            pbp_txt['plays']['start.is_home'] = np.where(
                pbp_txt['plays']["start.pos_team.id"].astype(int) == pbp_txt['plays']['homeTeamId'].astype(int),
                True, False
            )
            pbp_txt['plays']['end.is_home'] = np.where(
                pbp_txt['plays']["end.pos_team.id"].astype(int) == pbp_txt['plays']['homeTeamId'].astype(int),
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
                        (pbp_txt['plays']['period.number'] <= 2)].reset_index()['id']
            pbp_txt['timeouts'][homeTeamId]["2"] = pbp_txt['plays'].loc[
                        (pbp_txt['plays']['homeTimeoutCalled'] == True) &
                        (pbp_txt['plays']['period.number'] > 2)
                        ].reset_index()['id']
            pbp_txt['timeouts'][awayTeamId]["1"] = pbp_txt['plays'].loc[
                        (pbp_txt['plays']['awayTimeoutCalled'] == True) &
                        (pbp_txt['plays']['period.number'] <= 2)
                        ].reset_index()['id']
            pbp_txt['timeouts'][awayTeamId]["2"] = pbp_txt['plays'].loc[
                        (pbp_txt['plays']['awayTimeoutCalled'] == True) &
                        (pbp_txt['plays']['period.number'] > 2)
                        ].reset_index()['id']

            pbp_txt['timeouts'][homeTeamId]["1"] = pbp_txt['timeouts'][homeTeamId]["1"].apply(lambda x: int(x))
            pbp_txt['timeouts'][homeTeamId]["2"] = pbp_txt['timeouts'][homeTeamId]["2"].apply(lambda x: int(x))
            pbp_txt['timeouts'][awayTeamId]["1"] = pbp_txt['timeouts'][awayTeamId]["1"].apply(lambda x: int(x))
            pbp_txt['timeouts'][awayTeamId]["2"] = pbp_txt['timeouts'][awayTeamId]["2"].apply(lambda x: int(x))
            pbp_txt['plays']['end.homeTeamTimeouts'] = 3 - pbp_txt['plays'].apply(
                lambda x: ((pbp_txt['timeouts'][homeTeamId]["1"] <= x['id']) & (x['period.number'] <= 2))|
                        ((pbp_txt['timeouts'][homeTeamId]["2"] <= x['id']) & (x['period.number'] > 2)), axis = 1
            ).apply(lambda x: int(x.sum()), axis=1)
            pbp_txt['plays']['end.awayTeamTimeouts'] = 3 - pbp_txt['plays'].apply(
                lambda x: ((pbp_txt['timeouts'][awayTeamId]["1"] <= x['id']) & (x['period.number'] <= 2))|
                        ((pbp_txt['timeouts'][awayTeamId]["2"] <= x['id']) & (x['period.number'] > 2)), axis = 1
            ).apply(lambda x: int(x.sum()), axis=1)
            pbp_txt['plays']['start.homeTeamTimeouts'] = pbp_txt['plays']['end.homeTeamTimeouts'].shift(1)
            pbp_txt['plays']['start.awayTeamTimeouts'] = pbp_txt['plays']['end.awayTeamTimeouts'].shift(1)
            pbp_txt['plays']['start.homeTeamTimeouts'] = np.where(
                (pbp_txt['plays']['game_play_number'] == 1) |
                ((pbp_txt['plays']['half'] == "2") & (pbp_txt['plays']['lag_half'] == "1")),
                3, pbp_txt['plays']['start.homeTeamTimeouts']
            )
            pbp_txt['plays']['start.awayTeamTimeouts'] = np.where(
                (pbp_txt['plays']['game_play_number'] == 1)|
                ((pbp_txt['plays']['half'] == "2") & (pbp_txt['plays']['lag_half'] == "1")),
                3, pbp_txt['plays']['start.awayTeamTimeouts']
            )
            pbp_txt['plays']['start.homeTeamTimeouts'] = pbp_txt['plays']['start.homeTeamTimeouts'].apply(lambda x: int(x))
            pbp_txt['plays']['start.awayTeamTimeouts'] = pbp_txt['plays']['start.awayTeamTimeouts'].apply(lambda x: int(x))
            pbp_txt['plays']['end.TimeSecsRem'] = pbp_txt['plays']['start.TimeSecsRem'].shift(1)
            pbp_txt['plays']['end.adj_TimeSecsRem'] = pbp_txt['plays']['start.adj_TimeSecsRem'].shift(1)
            pbp_txt['plays']['end.TimeSecsRem'] = np.where(
                (pbp_txt['plays']['game_play_number'] == 1)|
                ((pbp_txt['plays']['half'] == "2") & (pbp_txt['plays']['lag_half'] == "1")),
                1800, pbp_txt['plays']['end.TimeSecsRem']
            )
            pbp_txt['plays']['end.adj_TimeSecsRem'] = np.select(
                [
                    (pbp_txt['plays']['game_play_number'] == 1),
                    ((pbp_txt['plays']['half'] == "2") & (pbp_txt['plays']['lag_half'] == "1"))
                ],
                [
                    3600,
                    1800
                ], default = pbp_txt['plays']['end.adj_TimeSecsRem']
            )
            pbp_txt['plays']['start.posTeamTimeouts'] = np.where(
                pbp_txt['plays']['start.pos_team.id'] == pbp_txt['plays']['homeTeamId'],
                pbp_txt['plays']['start.homeTeamTimeouts'],
                pbp_txt['plays']['start.awayTeamTimeouts']
            )
            pbp_txt['plays']['start.defPosTeamTimeouts'] = np.where(
                pbp_txt['plays']['start.def_pos_team.id'] == pbp_txt['plays']['homeTeamId'],
                pbp_txt['plays']['start.homeTeamTimeouts'],
                pbp_txt['plays']['start.awayTeamTimeouts']
            )
            pbp_txt['plays']['end.posTeamTimeouts'] = np.where(
                pbp_txt['plays']['end.pos_team.id'] == pbp_txt['plays']['homeTeamId'],
                pbp_txt['plays']['end.homeTeamTimeouts'],
                pbp_txt['plays']['end.awayTeamTimeouts']
            )
            pbp_txt['plays']['end.defPosTeamTimeouts'] = np.where(
                pbp_txt['plays']['end.def_pos_team.id'] == pbp_txt['plays']['homeTeamId'],
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
            pbp_txt['plays']['period'] = pbp_txt['plays']['period.number']
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

            pbp_txt['plays']['start.distance'] = np.where(
                (pbp_txt['plays']["start.distance"] == 0) & (pbp_txt['plays']["start.downDistanceText"].str.lower().str.contains("goal")), pbp_txt['plays']['start.yardsToEndzone'], pbp_txt['plays']['start.distance']
            )

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

            pbp_txt['plays']['playType'] = np.where(
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

        if 'scoringPlays' not in pbp_txt.keys():
            pbp_txt['scoringPlays']=np.array([])
        if 'winprobability' not in pbp_txt.keys():
            pbp_txt['winprobability'] = np.array([])
        if 'standings' not in pbp_txt.keys():
            pbp_txt['standings'] = np.array([])
        if 'videos' not in pbp_txt.keys():
            pbp_txt['videos'] = np.array([])
        if 'broadcasts' not in pbp_txt.keys():
            pbp_txt['broadcasts'] = np.array([])
        self.plays_json = pbp_txt['plays']
        pbp_json = {
            "drives" : pbp_txt['drives'],
            "scoringPlays" : np.array(pbp_txt['scoringPlays']).tolist(),
            "winprobability" : np.array(pbp_txt['winprobability']).tolist(),
            "boxscore" : pbp_txt['boxscore'],
            "header" : pbp_txt['header'],
            "homeTeamSpread" : np.array(pbp_txt['homeTeamSpread']).tolist(),
            "overUnder" : np.array(pbp_txt['overUnder']).tolist(),
            "broadcasts" : np.array(pbp_txt['broadcasts']).tolist(),
            "videos" : np.array(pbp_txt['videos']).tolist(),
            "standings" : pbp_txt['standings'],
            "timeouts" : pbp_txt['timeouts'],
            "pickcenter" : np.array(pbp_txt['pickcenter']).tolist(),
            "espnWP" : np.array(pbp_txt['espnWP']).tolist(),
            "gameInfo" : np.array(pbp_txt['gameInfo']).tolist(),
            "season" : np.array(pbp_txt['season']).tolist()
        }
        self.json = pbp_json
        return pbp_json


    def __setup_penalty_data(self, play_df):
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

        play_df['penalty_text'] = np.select(
            [
                (play_df.penalty_flag == True)
            ],
            [
                play_df.text.str.extract(r"Penalty(.+)", flags=re.IGNORECASE)[0]
            ], default = None
        )

        play_df['yds_penalty'] = np.select(
            [
                (play_df.penalty_flag == True)
            ],
            [
                play_df.penalty_text.str.extract("(.{0,3})yards|yds|yd to the ", flags=re.IGNORECASE)[0]
            ], default = None
        )
        play_df['yds_penalty'] = play_df['yds_penalty'].str.replace( " yards to the | yds to the | yd to the ", "")
        play_df['yds_penalty'] = np.select(
            [
                (play_df.penalty_flag == True) & (play_df.text.str.contains(r"ards\)", case=False, regex=True)) & (play_df.yds_penalty.isna()),
            ],
            [
                play_df.text.str.extract(r"(.{0,4})yards\)|Yards\)|yds\)|Yds\)",flags=re.IGNORECASE)[0]
            ], default = play_df.yds_penalty
        )
        play_df['yds_penalty'] = play_df.yds_penalty.str.replace( "yards\\)|Yards\\)|yds\\)|Yds\\)", "").str.replace( "\\(", "")
        return play_df

    def __add_downs_data(self, play_df):
        """
        Creates the following columns in play_df:
            * id, drive_id, game_id
            * down, ydstogo (distance), game_half, period
        """
        play_df = play_df.copy(deep=True)
        play_df.loc[:,"id"] = play_df.id.astype(float)
        play_df.sort_values(by=["id", "start.adj_TimeSecsRem"], inplace=True)
        play_df.drop_duplicates(subset=['text','id','type.text','start.down'], keep="last", inplace=True)
        play_df = play_df[(play_df['type.text'].str.contains("end of|coin toss|end period", case=False, regex=True) == False)]

        play_df.loc[:,"period"] = play_df["period.number"].astype(int)
        play_df.loc[(play_df.period <= 2), 'half'] = 1
        play_df.loc[(play_df.period > 2), 'half'] = 2
        play_df['lead_half'] = play_df.half.shift(-1)
        play_df['lag_scoringPlay'] = play_df.scoringPlay.shift(1)
        play_df.loc[play_df.lead_half.isna() == True, 'lead_half'] = 2
        play_df['end_of_half'] = (play_df.half != play_df.lead_half)

        play_df['down_1'] = (play_df["start.down"] == 1)
        play_df['down_2'] = (play_df["start.down"] == 2)
        play_df['down_3'] = (play_df["start.down"] == 3)
        play_df['down_4'] = (play_df["start.down"] == 4)

        play_df['down_1_end'] = (play_df["end.down"] == 1)
        play_df['down_2_end'] = (play_df["end.down"] == 2)
        play_df['down_3_end'] = (play_df["end.down"] == 3)
        play_df['down_4_end'] = (play_df["end.down"] == 4)
        return play_df

    def __add_play_type_flags(self, play_df):
        """
        Creates the following columns in play_df:
            * Flags for fumbles, scores, kickoffs, punts, field goals
        """
        #--- Touchdown, Fumble, Special Teams flags -----------------
        play_df.loc[:,"scoring_play"] = False
        play_df.loc[play_df["type.text"].isin(scores_vec), 'scoring_play'] = True
        play_df["td_play"] = play_df.text.str.contains(r"touchdown|for a TD", case=False, flags=0, na=False, regex=True)
        play_df["touchdown"] = play_df["type.text"].str.contains("touchdown", case=False, flags=0, na=False, regex=True)
        ## Portion of touchdown check for plays where touchdown is not listed in the play_type--
        play_df["td_check"] = play_df["text"].str.contains("Touchdown", case=False, flags=0, na=False, regex=True)
        play_df["safety"] = play_df["text"].str.contains("safety", case=False, flags=0, na=False, regex=True)
        #--- Fumbles----
        play_df["fumble_vec"] = np.select(
            [
                play_df["text"].str.contains("fumble", case=False, flags=0, na=False, regex=True),
                (~play_df["text"].str.contains("fumble", case=False, flags=0, na=False, regex=True)) & (play_df["type.text"] == "Rush") & (play_df["start.pos_team.id"] != play_df["end.pos_team.id"])
            ],
            [
                True,
                True
            ],
            default=False
        )
        play_df["forced_fumble"] = play_df["text"].str.contains("forced by", case=False, flags=0, na=False, regex=True)
        #--- Kicks----
        play_df["kickoff_play"] = (play_df["type.text"].isin(kickoff_vec))
        play_df["kickoff_tb"] = np.select(
            [
                (play_df["text"].str.contains("touchback", case=False, flags=0, na=False, regex=True)) & (play_df.kickoff_play == True),
                (play_df["text"].str.contains("kickoff$", case=False, flags=0, na=False, regex=True)) & (play_df.kickoff_play == True)
            ],
            [
                True,
                True
            ],
            default = False
        )
        play_df["kickoff_onside"] = (play_df["text"].str.contains(r"on-side|onside|on side", case=False, flags=0, na=False, regex=True)) & (play_df.kickoff_play == True)
        play_df["kickoff_oob"] = (play_df["text"].str.contains(r"out-of-bounds|out of bounds", case=False, flags=0, na=False, regex=True)) & (play_df.kickoff_play == True)
        play_df["kickoff_fair_catch"] = (play_df["text"].str.contains(r"fair catch|fair caught", case=False, flags=0, na=False, regex=True)) & (play_df.kickoff_play == True)
        play_df["kickoff_downed"] = (play_df["text"].str.contains("downed", case=False, flags=0, na=False, regex=True)) & (play_df.kickoff_play == True)
        play_df["kick_play"] = play_df["text"].str.contains(r"kick|kickoff", case=False, flags=0, na=False, regex=True)
        play_df["kickoff_safety"] = (~play_df["type.text"].isin(['Blocked Punt','Penalty'])) & (play_df["text"].str.contains("kickoff", case=False, flags=0, na=False, regex=True)) & (play_df.safety == True)
        #--- Punts----
        play_df["punt"] = np.where(play_df["type.text"].isin(punt_vec), True, False)
        play_df["punt_play"] = play_df["text"].str.contains("punt", case=False, flags=0, na=False, regex=True)
        play_df["punt_tb"] = np.where(
            (play_df["text"].str.contains("touchback", case=False, flags=0, na=False, regex=True)) &
            (play_df.punt == True), True, False
        )
        play_df["punt_oob"] = np.where(
            (play_df["text"].str.contains(r"out-of-bounds|out of bounds", case=False, flags=0, na=False, regex=True)) &
            (play_df.punt == True), True, False
        )
        play_df["punt_fair_catch"] = np.where(
            (play_df["text"].str.contains(r"fair catch|fair caught", case=False, flags=0, na=False, regex=True)) &
            (play_df.punt == True), True, False
        )
        play_df["punt_downed"] = np.where(
            (play_df["text"].str.contains("downed", case=False, flags=0, na=False, regex=True)) &
            (play_df.punt == True), True, False
        )
        play_df["punt_safety"] = np.where(
            (play_df["type.text"].isin(['Blocked Punt','Punt'])) &
            (play_df["text"].str.contains("punt", case=False, flags=0, na=False, regex=True)) &
            (play_df.safety == True), True, False
        )
        play_df["penalty_safety"] = np.where((play_df["type.text"].isin(['Penalty'])) & (play_df.safety == True), True, False)
        play_df["punt_blocked"] = np.where(
            (play_df["text"].str.contains("blocked", case=False, flags=0, na=False, regex=True)) & (play_df.punt == True), True, False
        )
        return play_df

    def __add_rush_pass_flags(self, play_df):
        """
        Creates the following columns in play_df:
            * Rush, Pass, Sacks
        """
        #--- Pass/Rush----
        play_df['rush'] = np.where(
            ((play_df["type.text"] == "Rush") |
             (play_df["type.text"] == "Rushing Touchdown") |
             (play_df["type.text"].isin(["Safety","Fumble Recovery (Opponent)","Fumble Recovery (Opponent) Touchdown", "Fumble Recovery (Own)", "Fumble Recovery (Own) Touchdown", "Fumble Return Touchdown"]) & play_df["text"].str.contains("run for"))),
            True, False
        )
        play_df['pass'] = np.where(
            (
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
            ),
            True, False
        )
        #--- Sacks----
        play_df['sack_vec'] = np.where(
            (
                (play_df["type.text"].isin(["Sack", "Sack Touchdown"])) |
                ((play_df["type.text"].isin(["Fumble Recovery (Own)", "Fumble Recovery (Own) Touchdown", "Fumble Recovery (Opponent)", "Fumble Recovery (Opponent) Touchdown", "Fumble Return Touchdown"]) &
                  (play_df["pass"] == True) &
                  (play_df["text"].str.contains("sacked", case=False, flags=0, na=False, regex=True))
                ))
            ), True, False
        )
        return play_df

    def __add_team_score_variables(self, play_df):
        """
        Creates the following columns in play_df:
            * Team Score variables
            * Fix change of poss variables
        """
        #-------------------------
        play_df['pos_team'] = play_df['start.pos_team.id']
        play_df['def_pos_team'] = play_df['start.def_pos_team.id']
        play_df['is_home'] = (play_df.pos_team == play_df["homeTeamId"])
        #--- Team Score variables ------
        play_df['lag_homeScore'] = play_df['homeScore'].shift(1)
        play_df['lag_awayScore'] = play_df['awayScore'].shift(1)
        play_df['lag_HA_score_diff'] = play_df['lag_homeScore'] - play_df['lag_awayScore']
        play_df['HA_score_diff'] = play_df['homeScore'] - play_df['awayScore']
        play_df['net_HA_score_pts'] = play_df['HA_score_diff'] - play_df['lag_HA_score_diff']
        play_df['H_score_diff'] = play_df['homeScore'] - play_df['lag_homeScore']
        play_df['A_score_diff'] = play_df['awayScore'] - play_df['lag_awayScore']
        play_df['homeScore'] = np.select(
            [
                (play_df.scoringPlay == False) & (play_df['game_play_number'] != 1) &
                (play_df['H_score_diff'] >= 9),
                (play_df.scoringPlay == False) & (play_df['game_play_number'] != 1) &
                (play_df['H_score_diff'] < 9) & (play_df['H_score_diff'] > 1),
                (play_df.scoringPlay == False) & (play_df['game_play_number'] != 1) &
                (play_df['H_score_diff'] >= -9) & (play_df['H_score_diff'] < -1)
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
                (play_df['A_score_diff'] >= 9),
                (play_df.scoringPlay == False) & (play_df['game_play_number'] != 1) &
                (play_df['A_score_diff'] < 9) & (play_df['A_score_diff'] > 1),
                (play_df.scoringPlay == False) & (play_df['game_play_number'] != 1) &
                (play_df['A_score_diff'] >= -9) & (play_df['A_score_diff'] < -1)],
            [
                play_df['lag_awayScore'],
                play_df['lag_awayScore'],
                play_df['awayScore']
            ], default = play_df['awayScore']
        )
        play_df.drop(['lag_homeScore','lag_awayScore'], axis=1, inplace=True)
        play_df['lag_homeScore'] = play_df['homeScore'].shift(1)
        play_df['lag_homeScore'] = np.where((play_df.lag_homeScore.isna()), 0, play_df['lag_homeScore'])
        play_df['lag_awayScore'] = play_df['awayScore'].shift(1)
        play_df['lag_awayScore'] = np.where((play_df.lag_awayScore.isna()), 0, play_df['lag_awayScore'])
        play_df['start.homeScore'] = np.where((play_df["game_play_number"] == 1), 0, play_df['lag_homeScore'])
        play_df['start.awayScore'] = np.where((play_df["game_play_number"] == 1), 0, play_df['lag_awayScore'])
        play_df['end.homeScore'] = play_df['homeScore']
        play_df['end.awayScore'] = play_df['awayScore']
        play_df['pos_team_score'] = np.where(play_df.pos_team == play_df["homeTeamId"], play_df.homeScore, play_df.awayScore)
        play_df['def_pos_team_score'] = np.where(play_df.pos_team == play_df["homeTeamId"], play_df.awayScore, play_df.homeScore)
        play_df['start.pos_team_score'] = np.where(play_df['start.pos_team.id'] == play_df["homeTeamId"], play_df['start.homeScore'], play_df['start.awayScore'])
        play_df['start.def_pos_team_score'] = np.where(play_df['start.pos_team.id'] == play_df["homeTeamId"], play_df['start.awayScore'], play_df['start.homeScore'])
        play_df['start.pos_score_diff'] = play_df['start.pos_team_score'] - play_df['start.def_pos_team_score']
        play_df['end.pos_team_score'] = np.where(play_df['end.pos_team.id'] == play_df["homeTeamId"], play_df['end.homeScore'], play_df['end.awayScore'])
        play_df['end.def_pos_team_score'] = np.where(play_df['end.pos_team.id'] == play_df["homeTeamId"], play_df['end.awayScore'], play_df['end.homeScore'])
        play_df['end.pos_score_diff'] = play_df['end.pos_team_score'] - play_df['end.def_pos_team_score']
        play_df['lag_pos_team'] = play_df['pos_team'].shift(1)
        play_df.loc[play_df.lag_pos_team.isna() == True, 'lag_pos_team'] = play_df.pos_team
        play_df['lead_pos_team'] = play_df['pos_team'].shift(-1)
        play_df['lead_pos_team2'] = play_df['pos_team'].shift(-2)
        play_df['pos_score_diff'] = play_df.pos_team_score - play_df.def_pos_team_score
        play_df['lag_pos_score_diff'] = play_df['pos_score_diff'].shift(1)
        play_df.loc[play_df.lag_pos_score_diff.isna(), 'lag_pos_score_diff'] = 0
        play_df['pos_score_pts'] = np.where(play_df.lag_pos_team == play_df.pos_team, play_df.pos_score_diff - play_df.lag_pos_score_diff, play_df.pos_score_diff + play_df.lag_pos_score_diff)
        play_df['pos_score_diff_start'] = np.select([
                (play_df.kickoff_play == True) & (play_df.lag_pos_team == play_df.pos_team),
                (play_df.kickoff_play == True) | (play_df.lag_pos_team != play_df.pos_team)
            ],
            [
                play_df.lag_pos_score_diff,
                -1 * play_df.lag_pos_score_diff
            ],
            default=play_df.lag_pos_score_diff
        )
        #--- Timeouts ------
        play_df.loc[play_df.pos_score_diff_start.isna() == True, 'pos_score_diff_start'] = play_df.pos_score_diff
        play_df['start.pos_team_receives_2H_kickoff'] = (play_df["start.pos_team.id"] == play_df.firstHalfKickoffTeamId)
        play_df['end.pos_team_receives_2H_kickoff'] = (play_df["end.pos_team.id"] == play_df.firstHalfKickoffTeamId)
        play_df['change_of_poss'] = np.where(play_df["start.pos_team.id"] == play_df["end.pos_team.id"], False, True)
        play_df['change_of_poss'] = np.where(play_df['change_of_poss'].isna(), 0, play_df['change_of_poss'])
        return play_df

    def __add_new_play_types(self, play_df):
        """
        Creates the following columns in play_df:
            * Fix play types
        """
        #--------------------------------------------------
        ## Fix Strip-Sacks to Fumbles----
        play_df['type.text'] = np.where(
            (play_df.fumble_vec == True) & (play_df["pass"] == True) &
            (play_df.change_of_poss == 1) & (play_df.td_play == False) &
            (play_df["start.down"] != 4) & ~(play_df['type.text'].isin(defense_score_vec)),
            "Fumble Recovery (Opponent)", play_df['type.text']
        )
        play_df['type.text'] = np.where(
            (play_df.fumble_vec == True) & (play_df["pass"] == True) &
            (play_df.change_of_poss == 1) & (play_df.td_play == True),
            "Fumble Recovery (Opponent) Touchdown", play_df['type.text']
        )
        ## Fix rushes with fumbles and a change of possession to fumbles----
        play_df['type.text'] = np.where(
            (play_df.fumble_vec == True) & (play_df["rush"] == True) &
            (play_df.change_of_poss == 1) & (play_df.td_play == False) &
            (play_df["start.down"] != 4) & ~(play_df['type.text'].isin(defense_score_vec)),
            "Fumble Recovery (Opponent)", play_df['type.text']
        )
        play_df['type.text'] = np.where(
            (play_df.fumble_vec == True) & (play_df["rush"] == True) &
            (play_df.change_of_poss == 1) & (play_df.td_play == True),
            "Fumble Recovery (Opponent) Touchdown", play_df['type.text']
        )

        #-- Fix kickoff fumble return TDs ----
        play_df['type.text'] = np.where(
            (play_df.kickoff_play == True) & (play_df.change_of_poss == 1) &
            (play_df.td_play == True) & (play_df.td_check == True),
            "Kickoff Return Touchdown", play_df['type.text']
        )
        #-- Fix punt return TDs ----
        play_df['type.text'] = np.where(
            (play_df.punt_play == True) & (play_df.td_play == True) &
            (play_df.td_check == True),
            "Punt Return Touchdown", play_df['type.text']
        )
        #-- Fix kick return TDs----
        play_df['type.text'] = np.where(
            (play_df.kickoff_play == True) & (play_df.fumble_vec == False) &
            (play_df.td_play == True) & (play_df.td_check == True),
            "Kickoff Return Touchdown", play_df['type.text']
        )
        #-- Fix rush/pass tds that aren't explicit----
        play_df['type.text'] = np.where(
            (play_df.td_play == True) &
            (play_df.rush == True) &
            (play_df.fumble_vec == False) &
            (play_df.td_check == True),
            "Rushing Touchdown", play_df['type.text']
        )
        play_df['type.text'] = np.where(
            (play_df.td_play == True) & (play_df["pass"] == True) &
            (play_df.fumble_vec == False) & (play_df.td_check == True) &
            ~(play_df['type.text'].isin(int_vec)),
            "Passing Touchdown", play_df['type.text']
        )
        play_df['type.text'] = np.where(
            (play_df["pass"] == True) &
            (play_df['type.text'].isin(["Pass Reception", "Pass Completion", "Pass"])) &
            (play_df.statYardage == play_df["start.yardsToEndzone"]) &
            (play_df.fumble_vec == False) & ~(play_df['type.text'].isin(int_vec)),
            "Passing Touchdown", play_df['type.text']
        )
        play_df['type.text'] = np.where(
            (play_df['type.text'].isin(["Blocked Field Goal"])) &
            (play_df['text'].str.contains("for a TD", case=False, flags=0, na=False, regex=True)),
            "Blocked Field Goal Touchdown", play_df['type.text']
        )

        play_df['type.text'] = np.where(
            (play_df['type.text'].isin(["Blocked Punt"])) &
            (play_df['text'].str.contains("for a TD", case=False, flags=0, na=False, regex=True)),
            "Blocked Punt Touchdown", play_df['type.text']
        )
        #-- Fix duplicated TD play_type labels----
        play_df['type.text'] = np.where(play_df['type.text'] == "Punt Touchdown Touchdown", "Punt Touchdown", play_df['type.text'])
        play_df['type.text'] = np.where(play_df['type.text'] == "Fumble Return Touchdown Touchdown", "Fumble Return Touchdown", play_df['type.text'])
        play_df['type.text'] = np.where(play_df['type.text'] == "Rushing Touchdown Touchdown", "Rushing Touchdown", play_df['type.text'])
        play_df['type.text'] = np.where(play_df['type.text'] == "Uncategorized Touchdown Touchdown", "Uncategorized Touchdown", play_df['type.text'])
        #-- Fix Pass Interception Return TD play_type labels----
        play_df['type.text'] = np.where(play_df["text"].str.contains("pass intercepted for a TD", case=False, flags=0, na=False, regex=True), "Interception Return Touchdown", play_df["type.text"])
        #-- Fix Sack/Fumbles Touchdown play_type labels----
        play_df['type.text'] = np.where(
            (play_df["text"].str.contains("sacked", case=False, flags=0, na=False, regex=True)) &
            (play_df["text"].str.contains("fumbled", case=False, flags=0, na=False, regex=True)) &
            (play_df["text"].str.contains("TD", case=False, flags=0, na=False, regex=True)),
            "Fumble Recovery (Opponent) Touchdown", play_df["type.text"]
        )
        #-- Fix generic pass plays ----
        ##-- first one looks for complete pass
        play_df['type.text'] = np.where(
            (play_df['type.text'] == "Pass") &
            (play_df.text.str.contains("pass complete", case=False, flags=0, na=False, regex=True)),
            "Pass Completion", play_df['type.text']
        )
        ##-- second one looks for incomplete pass
        play_df['type.text'] = np.where(
            (play_df['type.text'] == "Pass") &
            (play_df.text.str.contains("pass incomplete", case=False, flags=0, na=False, regex=True)),
            "Pass Incompletion", play_df['type.text']
        )
        ##-- third one looks for interceptions
        play_df['type.text'] = np.where(
            (play_df['type.text'] == "Pass") &
            (play_df.text.str.contains("pass intercepted", case=False, flags=0, na=False, regex=True)),
            "Pass Interception", play_df['type.text']
        )
        ##-- fourth one looks for sacked
        play_df['type.text'] = np.where(
            (play_df['type.text'] == "Pass") &
            (play_df.text.str.contains("sacked", case=False, flags=0, na=False, regex=True)),
            "Sack", play_df['type.text']
        )
        ##-- fifth one play type is Passing Touchdown, but its intercepted
        play_df['type.text'] = np.where(
            (play_df['type.text'] == "Passing Touchdown") &
            (play_df.text.str.contains("pass intercepted for a TD", case=False, flags=0, na=False, regex=True)),
            "Interception Return Touchdown", play_df['type.text']
        )
        play_df['type.text'] = np.where(
            (play_df['type.text'] == "Passing Touchdown") &
            (play_df.text.str.contains("pass intercepted for a TD", case=False, flags=0, na=False, regex=True)),
            "Interception Return Touchdown", play_df['type.text']
        )
        #--- Moving non-Touchdown pass interceptions to one play_type: "Interception Return" -----
        play_df['type.text'] = np.where(play_df['type.text'].isin(["Interception"]), "Interception Return", play_df['type.text'])
        play_df['type.text'] = np.where(play_df['type.text'].isin(["Pass Interception"]), "Interception Return", play_df['type.text'])
        play_df['type.text'] = np.where(play_df['type.text'].isin(["Pass Interception Return"]), "Interception Return", play_df['type.text'])

        #--- Moving Kickoff/Punt Touchdowns without fumbles to Kickoff/Punt Return Touchdown
        play_df['type.text'] = np.where(
            (play_df['type.text'] == "Kickoff Touchdown") &
            (play_df.fumble_vec == False),
            "Kickoff Return Touchdown", play_df['type.text']
        )

        play_df['type.text'] = np.where(
            (play_df['type.text'].isin(["Kickoff", "Kickoff Return (Offense)"])) &
            (play_df.fumble_vec == True) & (play_df.change_of_poss == 1),
            "Kickoff Team Fumble Recovery", play_df['type.text']
        )

        play_df['type.text'] = np.select(
            [
                (play_df['type.text'] == "Punt Touchdown") & (play_df.fumble_vec == False) & (play_df.change_of_poss == 1),
                (play_df["type.text"] == "Punt") & (play_df.text.str.contains("for a TD", case=False, flags=0, na=False, regex=True)) & (play_df.change_of_poss == 1)
            ],
            [
                "Punt Return Touchdown",
                "Punt Return Touchdown"
            ],
            default = play_df["type.text"]
        )

        play_df['type.text'] = np.where(
            (play_df['type.text'] == "Punt") & (play_df.fumble_vec == True) &
            (play_df.change_of_poss == 0),
            "Punt Team Fumble Recovery", play_df['type.text']
        )
        play_df['type.text'] = np.where(
            (play_df['type.text'].isin(["Punt Touchdown"]))|
            ((play_df['scoringPlay']==True) & (play_df["punt_play"] == True) & (play_df.change_of_poss == 0)),
            "Punt Team Fumble Recovery Touchdown", play_df['type.text']
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
        return play_df

    def __add_play_category_flags(self, play_df):
        #--------------------------------------------------
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
        play_df["completion"] = np.select(
            [
                play_df['type.text'].isin(["Pass Reception", "Pass Completion", "Passing Touchdown"]),
                (play_df['type.text'].isin(["Fumble Recovery (Own)", "Fumble Recovery (Own) Touchdown", "Fumble Recovery (Opponent)", "Fumble Recovery (Opponent) Touchdown"]) & (play_df['pass'] == True) & ~(play_df["text"].str.contains("sacked", case=False, flags=0, na=False, regex=True)))
            ],
            [
                True,
                True
            ],
            default=False
        )

        play_df["pass_attempt"] = np.select(
            [
                (play_df['type.text'].isin(["Pass Reception", "Pass Completion", "Passing Touchdown", "Pass Incompletion"])),
                (play_df['type.text'].isin(["Fumble Recovery (Own)", "Fumble Recovery (Own) Touchdown", "Fumble Recovery (Opponent)", "Fumble Recovery (Opponent) Touchdown"]) & (play_df['pass'] == True) & ~(play_df["text"].str.contains("sacked", case=False, flags=0, na=False, regex=True))),
                ((play_df['pass'] == True) & ~(play_df["text"].str.contains("sacked", case=False, flags=0, na=False, regex=True)))
            ],
            [
                True,
                True,
                True
            ],
            default=False
        )

        play_df['target'] = np.select(
            [
                (play_df['type.text'].isin(["Pass Reception", "Pass Completion", "Passing Touchdown", "Pass Incompletion"])),
                (play_df['type.text'].isin(["Fumble Recovery (Own)", "Fumble Recovery (Own) Touchdown", "Fumble Recovery (Opponent)", "Fumble Recovery (Opponent) Touchdown"]) & (play_df['pass'] == True) & ~(play_df["text"].str.contains("sacked", case=False, flags=0, na=False, regex=True))),
                ((play_df['pass'] == True) & ~(play_df["text"].str.contains("sacked", case=False, flags=0, na=False, regex=True)))
            ],
            [
                True,
                True,
                True
            ],
            default=False
        )

        play_df['pass_breakup'] = play_df['text'].str.contains('broken up by', case=False, flags=0, na=False, regex=True)
        #--- Pass/Rush TDs ------
        play_df['pass_td'] = (play_df["type.text"] == "Passing Touchdown") | ((play_df["pass"] == True) & (play_df["td_play"] == True))
        play_df['rush_td'] = (play_df["type.text"] == "Rushing Touchdown") | ((play_df["rush"] == True) & (play_df["td_play"] == True))
        #--- Change of possession via turnover
        play_df['turnover_vec'] = play_df["type.text"].isin(turnover_vec)
        play_df['offense_score_play'] = play_df["type.text"].isin(offense_score_vec)
        play_df['defense_score_play'] = play_df["type.text"].isin(defense_score_vec)
        play_df['downs_turnover'] = np.where(
            (play_df["type.text"].isin(normalplay)) &
            (play_df["statYardage"] < play_df["start.distance"]) &
            (play_df["start.down"] == 4) &
            (play_df["penalty_1st_conv"] == False),
            True, False
        )
        #--- Touchdowns----
        play_df['scoring_play'] = play_df["type.text"].isin(scores_vec)
        play_df['yds_punted'] = play_df["text"].str.extract(r"(?<= punt for)[^,]+(\d+)", flags=re.IGNORECASE).astype(float)
        play_df['yds_punt_gained'] = np.where(play_df.punt == True, play_df["statYardage"], None)
        play_df['fg_attempt'] =  np.where(
            (play_df["type.text"].str.contains("Field Goal", case=False, flags=0, na=False, regex=True))|
            (play_df["text"].str.contains("Field Goal", case=False, flags=0, na=False, regex=True)),
            True, False
        )
        play_df['fg_made'] = (play_df["type.text"] == "Field Goal Good")
        play_df['yds_fg'] = play_df["text"].str.extract(r"(\\d{0,2}\s?)Yd|(\\d{0,2}\s?)Yard FG|(\\d{0,2}\s?)Field|(\\d{0,2}\s?)Yard Field", 
                                                        flags=re.IGNORECASE).bfill(axis=1)[0].astype(float)
        #--------------------------------------------------
        play_df['start.yardsToEndzone'] = np.where(
            play_df['fg_attempt'] == True,
            play_df['yds_fg'] - 17, play_df["start.yardsToEndzone"]
        )
        play_df["start.yardsToEndzone"] = np.select(
            [
                (play_df["start.yardsToEndzone"].isna()) &
                (~play_df["type.text"].isin(kickoff_vec)) &
                (play_df['start.pos_team.id'] == play_df["homeTeamId"]),
                (play_df["start.yardsToEndzone"].isna()) &
                (~play_df["type.text"].isin(kickoff_vec)) &
                (play_df['start.pos_team.id'] == play_df["awayTeamId"])
            ],
            [
                100-play_df["start.yardLine"].astype(float),
                play_df["start.yardLine"].astype(float)
            ], default = play_df["start.yardsToEndzone"]
        )
        play_df["pos_unit"] = np.select(
            [
                play_df.punt == True,
                play_df.kickoff_play == True,
                play_df.fg_attempt == True,
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
                play_df.fg_attempt == True,
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

        play_df['sp'] = np.where(
           (play_df.fg_attempt == True) | (play_df.punt == True) | (play_df.kickoff_play == True), True, False
        )
        play_df['play'] = np.where(
            (~play_df['type.text'].isin(['Timeout','End Period', 'End of Half','Penalty'])), True, False
        )
        play_df['scrimmage_play'] = np.where(
            (play_df.sp == False) & 
            (~play_df['type.text'].isin(['Timeout','Extra Point Good','Extra Point Missed','Two-Point Pass','Two-Point Rush', 'Penalty'])), 
            True, False
        )
        #--------------------------------------------------
        #--- Change of pos_team by lead('pos_team', 1)----
        play_df['change_of_pos_team'] = np.where(
            (play_df.pos_team == play_df.lead_pos_team) & (~(play_df.lead_play_type.isin(["End Period", "End of Half"])) | play_df.lead_play_type.isna() == True),
            False,
            np.where(
                (play_df.pos_team == play_df.lead_pos_team2) &
                ((play_df.lead_play_type.isin(["End Period", "End of Half"])) | play_df.lead_play_type.isna() == True),
                False, True
            )
        )
        play_df['change_of_pos_team'] = np.where(play_df['change_of_poss'].isna(), False, play_df['change_of_pos_team'])
        play_df["pos_score_diff_end"] = np.where(
            ((play_df["type.text"].isin(end_change_vec)) & (play_df["start.pos_team.id"] != play_df["end.pos_team.id"])) | (play_df.downs_turnover == True),
            -1*play_df.pos_score_diff,  play_df.pos_score_diff
        )
        play_df['pos_score_diff_end'] = np.select(
            [
                (abs(play_df.pos_score_pts) >= 8) & (play_df.scoring_play == False) & (play_df.change_of_pos_team == False),
                (abs(play_df.pos_score_pts) >= 8) & (play_df.scoring_play == False) & (play_df.change_of_pos_team == True)
            ],
            [
                play_df['pos_score_diff_start'], -1*play_df['pos_score_diff_start']
            ], default = play_df['pos_score_diff_end']
        )

        play_df["fumble_lost"] = np.where(
            (play_df.fumble_vec == True) & (play_df.change_of_poss == True), True, False
        )
        play_df["fumble_recovered"] = np.where(
            (play_df.fumble_vec == True) & (play_df.change_of_poss == False), True, False
        )
        return play_df

    def __add_yardage_cols(self, play_df):
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
                (play_df["pass"] == True) & (play_df.text.str.contains("complete to", case=False)),
                (play_df["pass"] == True) & (play_df.text.str.contains("incomplete", case=False)),
                (play_df["pass"] == True) & (play_df["type.text"].str.contains("incompletion", case=False)),
                (play_df["pass"] == True) & (play_df.text.str.contains("Yd pass", case=False)),
            ],
            [
                0.0,
                -1 * play_df.text.str.extract(r"((?<=for a loss of)[^,]+)", flags=re.IGNORECASE)[0].str.extract(r"(\d+)")[0].astype(float),
                play_df.text.str.extract(r"((?<=for)[^,]+)", flags=re.IGNORECASE)[0].str.extract(r"(\d+)")[0].astype(float),
                play_df.text.str.extract(r"((?<=for)[^,]+)", flags=re.IGNORECASE)[0].str.extract(r"(\d+)")[0].astype(float),
                0.0,
                0.0,
                play_df.text.str.extract(r"(\d+)\s+Yd\s+pass", flags=re.IGNORECASE)[0].str.extract(r"(\d+)")[0].astype(float),
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
                (play_df.kickoff_play == True) & (play_df.fumble_vec == False) & (play_df.text.str.contains(r"for no gain|fair catch|fair caught", regex=True,case = False)),
                (play_df.kickoff_play == True) & (play_df.fumble_vec == False) & (play_df.text.str.contains(r"out-of-bounds|out of bounds", regex=True,case = False)),
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
                (play_df.fumble_vec == True) & (play_df.kickoff_play == False)
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
        return play_df

    def __add_player_cols(self, play_df):
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
            play_df.text.str.extract("(.+)pass(.+)? complete to")[0],
            play_df['pass_player']
        )
        play_df['pass_player'] = play_df.pass_player.str.replace(" pass complete to(.+)", "", regex=True)
        play_df['pass_player'] = play_df.pass_player.str.replace(" pass complete to", "", regex=True)
        
        play_df['pass_player'] = np.where(
            (play_df["type.text"] == "Passing Touchdown") & play_df.pass_player.isna(),
            play_df.text.str.extract("(.+)pass,to")[0],
            play_df['pass_player']
        )
        
        play_df['pass_player'] = play_df.pass_player.str.replace(" pass,to(.+)", "", regex=True)
        play_df['pass_player'] = play_df.pass_player.str.replace(" pass,to", "", regex=True)
        play_df['pass_player'] = play_df.pass_player.str.replace(" \((.+)\)", "", regex=True)
        play_df['pass_player'] = np.where(
            (play_df["pass"] == 1) & ((play_df.pass_player.str.strip().str.len == 0) | play_df.pass_player.isna()),
            "TEAM",
            play_df.pass_player
        )
        
        play_df['receiver_player'] = np.where(
            (play_df["pass"] == 1) & ~play_df.text.str.contains("sacked", case=False, flags=0, na=False, regex=True),
            play_df.text.str.extract("to (.+)")[0],
            None
        )
        
        play_df['receiver_player'] = np.where(
            play_df.text.str.contains("Yd pass", case=False, flags=0, na=False, regex=True),
            play_df.text.str.extract("(.{0,25} )\\d{0,2} Yd pass", flags=re.IGNORECASE)[0],
            play_df['receiver_player']
        )
            
        play_df['receiver_player'] = np.where(
            play_df.text.str.contains("Yd TD pass", case=False),
            play_df.text.str.extract("(.{0,25} )\\d{0,2} Yd TD pass", flags=re.IGNORECASE)[0],
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
        play_df.receiver_player = play_df.receiver_player.str.replace("\\,.+", "", case=False,regex=True)
        play_df.receiver_player = play_df.receiver_player.str.replace("for (.+)", "", case=False,regex=True)
        play_df.receiver_player = play_df.receiver_player.str.replace(r" (\d{1,2})", "", case=False,regex=True)
        play_df.receiver_player = play_df.receiver_player.str.replace(" Yd pass", "", case=False,regex=True)
        play_df.receiver_player = play_df.receiver_player.str.replace(" Yd TD pass", "", case=False,regex=True)
        play_df.receiver_player = play_df.receiver_player.str.replace("pass complete to", "", case=False,regex=True)
        play_df.receiver_player = play_df.receiver_player.str.replace("penalty", "", case=False,regex=True)
        play_df.receiver_player = play_df.receiver_player.str.replace(" \"", "", case=False,regex=True)
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
        
        play_df['sack_players'] = np.where(
            (play_df["sack"] == True) | (play_df["fumble_vec"] == True) & (play_df["pass"] == True) ,
            play_df.text.str.extract("sacked by(.+)", flags=re.IGNORECASE)[0],
            play_df.sack_players
        )
        
        play_df['sack_players'] = play_df['sack_players'].str.replace("for (.+)","", case=True, regex=True)
        play_df['sack_players'] = play_df['sack_players'].str.replace("(.+) by ","", case=True, regex=True)
        play_df['sack_players'] = play_df['sack_players'].str.replace(" at the (.+)","", case=True, regex=True)
        play_df['sack_player1'] = play_df['sack_players'].str.replace("and (.+)","", case=True, regex=True)
        play_df['sack_player2'] = np.where(play_df['sack_players'].str.contains("and (.+)"),
                                        play_df['sack_players'].str.replace("(.+) and","", case=True, regex=True),
                                        None)
        
        play_df['interception_player'] = np.where(
            (play_df["type.text"] == "Interception Return") | (play_df["type.text"] == "Interception Return Touchdown") & 
            play_df['pass'] == True, play_df.text.str.extract('intercepted (.+)', flags=re.IGNORECASE)[0], 
            play_df.interception_player
        )
        
        play_df['interception_player'] = np.where(
            play_df.text.str.contains('Yd Interception Return', case=True, regex=True),
            play_df.text.str.extract('(.{0,25} )\\d{0,2} Yd Interception Return|(.{0,25} )\\d{0,2} yd interception return', flags=re.IGNORECASE).bfill(axis=1)[0],
            play_df.interception_player
        )
        play_df['interception_player'] = play_df['interception_player'].str.replace("return (.+)","", case = True, regex = True)
        play_df['interception_player'] = play_df['interception_player'].str.replace("(.+) intercepted","", case = True, regex = True)
        play_df['interception_player'] = play_df['interception_player'].str.replace("intercepted","", case = True, regex = True)
        play_df['interception_player'] = play_df['interception_player'].str.replace("Yd Interception Return","", regex = True)
        play_df['interception_player'] = play_df['interception_player'].str.replace("for a 1st down","", case = True, regex = True)
        play_df['interception_player'] = play_df['interception_player'].str.replace("(\\d{1,2})","", case = True, regex = True)
        play_df['interception_player'] = play_df['interception_player'].str.replace("for a TD","", case = True, regex = True)
        play_df['interception_player'] = play_df['interception_player'].str.replace("at the (.+)","", case = True, regex = True)
        play_df['interception_player'] = play_df['interception_player'].str.replace(" by ","", case = True, regex = True)

        play_df['pass_breakup_player'] = np.where(
            play_df["pass"] == True, play_df.text.str.extract("broken up by (.+)"), play_df.pass_breakup_player
        )
        play_df['pass_breakup_player'] = play_df['pass_breakup_player'].str.replace("(.+) broken up by", "", case = True, regex = True)
        play_df['pass_breakup_player'] = play_df['pass_breakup_player'].str.replace("broken up by", "", case = True, regex = True)
        play_df['pass_breakup_player'] = play_df['pass_breakup_player'].str.replace("Penalty(.+)", "", case = True, regex = True)
        play_df['pass_breakup_player'] = play_df['pass_breakup_player'].str.replace("SOUTH FLORIDA", "", case = True, regex = True)
        play_df['pass_breakup_player'] = play_df['pass_breakup_player'].str.replace("WEST VIRGINIA", "", case = True, regex = True)
        play_df['pass_breakup_player'] = play_df['pass_breakup_player'].str.replace("MISSISSIPPI ST", "", case = True, regex = True)
        play_df['pass_breakup_player'] = play_df['pass_breakup_player'].str.replace("CAMPBELL", "", case = True, regex = True)
        play_df['pass_breakup_player'] = play_df['pass_breakup_player'].str.replace("COASTL CAROLINA", "", case = True, regex = True)

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
        play_df["punt_block_return_player"] = play_df["punt_block_return_player"].str.replace("(.+)blocked by {punt_block_player}","")
        play_df["punt_block_return_player"] = play_df["punt_block_return_player"].str.replace("blocked by {punt_block_player}","")
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
        play_df["kickoff_return_player"] = play_df["kickoff_return_player"].str.replace(" return| fumble| returned by| for |touchback by ", "", case=False, regex=True)
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
        
        play_df["fumble_player"] = np.where(
            play_df["text"].str.contains("fumble", case=False, flags=0, na=False, regex=True),
            play_df["text"].str.extract("(.{0,25} )fumble"),
            play_df.fumble_player
        )
        play_df["fumble_player"] = play_df["fumble_player"].str.replace(" fumble(.+)", "", case = False, regex = True)
        play_df["fumble_player"] = play_df["fumble_player"].str.replace("fumble", "", case = False, regex = True)
        play_df["fumble_player"] = play_df["fumble_player"].str.replace(" yds", "", case = False, regex = True)
        play_df["fumble_player"] = play_df["fumble_player"].str.replace(" yd", "", case = False, regex = True)
        play_df["fumble_player"] = play_df["fumble_player"].str.replace("yardline", "", case = False, regex = True)
        play_df["fumble_player"] = play_df["fumble_player"].str.replace(" yards| yard|for a TD|or a safety", "", case = False, regex = True)
        play_df["fumble_player"] = play_df["fumble_player"].str.replace(" for ", "", case = False, regex = True)
        play_df["fumble_player"] = play_df["fumble_player"].str.replace(" a safety", "", case = False, regex = True)
        play_df["fumble_player"] = play_df["fumble_player"].str.replace("r no gain", "", case = False, regex = True)
        play_df["fumble_player"] = play_df["fumble_player"].str.replace("(.+)(\\d{1,2})", "", case = False, regex = True)
        play_df["fumble_player"] = play_df["fumble_player"].str.replace("(\\d{1,2})", "", case = False, regex = True)
        play_df["fumble_player"] = play_df["fumble_player"].str.replace(", ", "", case = False, regex = True)
        play_df["fumble_player"] = np.where(play_df["type.text"] == "Penalty", None, play_df.fumble_player)
        
        play_df["fumble_forced_player"] = np.where(
            (play_df.text.str.contains("fumble", case=False, flags=0, na=False, regex=True)) & 
            (play_df.text.str.contains("forced by", case=False, flags=0, na=False, regex=True)),
            play_df.text.str.extract("forced by(.{0,25})"), 
            play_df.fumble_forced_player)
        
        play_df["fumble_forced_player"] = play_df["fumble_forced_player"].str.replace("(.+)forced by", "", case = False, regex = True)
        play_df["fumble_forced_player"] = play_df["fumble_forced_player"].str.replace("forced by", "", case = False, regex = True)
        play_df["fumble_forced_player"] = play_df["fumble_forced_player"].str.replace(", recove(.+)", "", case = False, regex = True)
        play_df["fumble_forced_player"] = play_df["fumble_forced_player"].str.replace(", re(.+)", "", case = False, regex = True)
        play_df["fumble_forced_player"] = play_df["fumble_forced_player"].str.replace(", fo(.+)", "", case = False, regex = True)
        play_df["fumble_forced_player"] = play_df["fumble_forced_player"].str.replace(", r", "", case = False, regex = True)
        play_df["fumble_forced_player"] = play_df["fumble_forced_player"].str.replace(", ", "", case = False, regex = True)
        play_df["fumble_forced_player"] = np.where(play_df["type.text"] == "Penalty", None, play_df.fumble_forced_player)
        
        play_df["fumble_recovered_player"] = np.where(
            (play_df.text.str.contains("fumble", case=False, flags=0, na=False, regex=True)) & 
            (play_df.text.str.contains("recovered by", case=False, flags=0, na=False, regex=True)),
            play_df.text.str.extract("recovered by(.{0,30})"), 
            play_df.fumble_recovered_player)
        
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
        play_df["fumble_recovered_player"] = np.where(play_df["type.text"] == "Penalty", None, play_df.fumble_recovered_player)

        ## Extract player names
        play_df['passer_player_name'] = play_df['pass_player'].str.strip()
        play_df['rusher_player_name'] = play_df['rush_player'].str.strip()
        play_df['receiver_player_name'] = play_df['receiver_player'].str.strip()
        play_df['sack_player_name'] = play_df['sack_player1'].str.strip()
        play_df['sack_player_name2'] = play_df['sack_player2'].str.strip()
        play_df['pass_breakup_player_name'] = play_df['pass_breakup_player'].str.strip()
        play_df['interception_player_name'] = play_df['interception_player'].str.strip()
        play_df['fg_kicker_player_name'] = play_df['fg_kicker_player'].str.strip()
        play_df['fg_block_player_name'] = play_df['fg_block_player'].str.strip()
        play_df['fg_return_player_name'] = play_df['fg_return_player'].str.strip()
        play_df['kickoff_player_name'] = play_df['kickoff_player'].str.strip()
        play_df['kickoff_return_player_name'] = play_df['kickoff_return_player'].str.strip()
        play_df['punter_player_name'] = play_df['punter_player'].str.strip()
        play_df['punt_block_player_name'] = play_df['punt_block_player'].str.strip()
        play_df['punt_return_player_name'] = play_df['punt_return_player'].str.strip()
        play_df['punt_block_return_player_name'] = play_df['punt_block_return_player'].str.strip()
        play_df['fumble_player_name'] = play_df['fumble_player'].str.strip()
        play_df['fumble_forced_player_name'] = play_df['fumble_forced_player'].str.strip()
        play_df['fumble_recovered_player_name'] = play_df['fumble_recovered_player'].str.strip()

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

    def __after_cols(self, play_df):
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
                    (play_df['statYardage'] < play_df['start.distance']) & (play_df['start.down']<=3),
                (play_df["type.text"].isin(penalty)) & (play_df["penalty_1st_conv"]==False) &
                    (play_df["penalty_offset"]==True) & (play_df["penalty_declined"]==True) &
                    (play_df['statYardage'] < play_df['start.distance']) & (play_df['start.down']==4),
                (play_df["type.text"].isin(penalty)) & (play_df["penalty_1st_conv"]==False) &
                    (play_df["penalty_offset"]==True) & (play_df["penalty_declined"]==True) &
                    (play_df['statYardage'] >= play_df['start.distance']),
                # only penalty declined true, same logic as prior (1 case, split in three)
                (play_df["type.text"].isin(penalty)) & (play_df["penalty_1st_conv"]==False) &
                    (play_df["penalty_offset"]==False) & (play_df["penalty_declined"]==True) &
                    (play_df['statYardage'] < play_df['start.distance']) & (play_df['start.down']<=3),
                (play_df["type.text"].isin(penalty)) & (play_df["penalty_1st_conv"]==False) &
                    (play_df["penalty_offset"]==False) & (play_df["penalty_declined"]==True) &
                    (play_df['statYardage'] < play_df['start.distance']) & (play_df['start.down']==4),
                (play_df["type.text"].isin(penalty)) & (play_df["penalty_1st_conv"]==False) &
                    (play_df["penalty_offset"]==False) & (play_df["penalty_declined"]==True) &
                    (play_df['statYardage'] >= play_df['start.distance']),
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
        play_df['new_distance'] =  np.select(
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
                    (play_df['statYardage'] < play_df['start.distance']) & (play_df['start.down']<=3),
                (play_df["type.text"].isin(penalty)) & (play_df["penalty_1st_conv"]==False) &
                    (play_df["penalty_offset"]==True) & (play_df["penalty_declined"]==True) &
                    (play_df['statYardage'] < play_df['start.distance']) & (play_df['start.down']==4),
                (play_df["type.text"].isin(penalty)) & (play_df["penalty_1st_conv"]==False) &
                    (play_df["penalty_offset"]==True) & (play_df["penalty_declined"]==True) &
                    (play_df['statYardage'] >= play_df['start.distance']),
                # only penalty declined true, same logic as prior (1 case, split in three)
                (play_df["type.text"].isin(penalty)) & (play_df["penalty_1st_conv"]==False) &
                    (play_df["penalty_offset"]==False) & (play_df["penalty_declined"]==True) &
                    (play_df['statYardage'] < play_df['start.distance']) & (play_df['start.down']<=3),
                (play_df["type.text"].isin(penalty)) & (play_df["penalty_1st_conv"]==False) &
                    (play_df["penalty_offset"]==False) & (play_df["penalty_declined"]==True) &
                    (play_df['statYardage'] < play_df['start.distance']) & (play_df['start.down']==4),
                (play_df["type.text"].isin(penalty)) & (play_df["penalty_1st_conv"]==False) &
                    (play_df["penalty_offset"]==False) & (play_df["penalty_declined"]==True) &
                    (play_df['statYardage'] >= play_df['start.distance']),
            ],
            [
                play_df['start.distance'],
                10,
                play_df['start.distance'],
                play_df['start.distance'] - play_df['statYardage'],
                10,
                10,
                play_df['start.distance'] - play_df['statYardage'],
                10,
                10,
            ], default = play_df['start.distance']
        )

        play_df['middle_8'] =  np.where((play_df['start.adj_TimeSecsRem'] >= 1560) & (play_df['start.adj_TimeSecsRem'] <= 2040), True, False)
        play_df['rz_play'] =  np.where(play_df['start.yardsToEndzone'] <= 20, True, False)
        play_df['scoring_opp'] =  np.where(play_df['start.yardsToEndzone'] <= 40, True, False)
        play_df['stuffed_run'] =  np.where((play_df.rush == True) & (play_df.yds_rushed <= 0), True, False)
        play_df['stopped_run'] =  np.where((play_df.rush == True) & (play_df.yds_rushed <= 2), True, False)
        play_df['opportunity_run'] =  np.where((play_df.rush == True) & (play_df.yds_rushed >= 4), True, False)
        play_df['highlight_run'] =  np.where((play_df.rush == True) & (play_df.yds_rushed >= 8), True, False)

        play_df['line_yards'] = np.select(
            [
                (play_df.rush == 1) & (play_df.yds_rushed < 0),
                (play_df.rush == 1) & (play_df.yds_rushed >= 0) & (play_df.yds_rushed <= 4),
                (play_df.rush == 1) & (play_df.yds_rushed >= 5) & (play_df.yds_rushed <= 10),
                (play_df.rush == 1) & (play_df.yds_rushed >= 11)
            ],
            [
                1.2 * play_df.yds_rushed,
                play_df.yds_rushed,
                0.5 * play_df.yds_rushed,
                0.0
            ],
            default=None
        )

        play_df['highlight_yards'] = np.select(
            [
                (play_df.rush == 1) & (play_df.yds_rushed > 4),
                (play_df.rush == 1)
            ],
            [
                (play_df.yds_rushed - play_df.line_yards),
                0.0
            ],
            default=None
        )

        play_df['opp_highlight_yards'] = np.select(
            [
                (play_df.opportunity_run == True),
                (play_df.opportunity_run == False) & (play_df.rush == 1)
            ],
            [
                play_df['highlight_yards'],
                0.0
            ],
            default=None
        )

        play_df['second_level_yards'] = np.where((play_df.rush == 1) & (play_df.yds_rushed >= 5) & (play_df.yds_rushed <= 10), play_df.yds_rushed, None)
        play_df['open_field_yards'] = np.where((play_df.rush == 1) & (play_df.yds_rushed >= 11), play_df.yds_rushed, None)

        play_df['short_rush_success'] = np.where(
            (play_df['start.distance'] < 2) & (play_df.rush == True) & (play_df.statYardage >= play_df['start.distance']), True, False
        )
        play_df['short_rush_attempt'] = np.where(
            (play_df['start.distance'] < 2) & (play_df.rush == True), True, False
        )
        play_df['power_rush_success'] = np.where(
            (play_df['start.distance'] < 2) & (play_df['start.down'].isin([3, 4])) & (play_df.rush == True) & (play_df.statYardage >= play_df['start.distance']), True, False
        )
        play_df['power_rush_attempt'] = np.where(
            (play_df['start.distance'] < 2) & (play_df['start.down'].isin([3, 4])) & (play_df.rush == True), True, False
        )
        play_df['early_down'] = np.where(
            ((play_df.down_1 == True) | (play_df.down_2 == True)) & (play_df.scrimmage_play == True), True, False
        )
        play_df['late_down'] = np.where(
            (play_df.early_down == False) & (play_df.scrimmage_play == True), True, False
        )
        play_df['early_down_pass'] =  np.where(
            (play_df["pass"] == 1) & (play_df.early_down == True), True, False
        )
        play_df['early_down_rush'] =  np.where(
            (play_df["rush"] == 1) & (play_df.early_down == True), True, False
        )
        play_df['late_down_pass'] =  np.where(
            (play_df["pass"] == 1) & (play_df.late_down == True), True, False
        )
        play_df['late_down_rush'] =  np.where(
            (play_df["rush"] == 1) & (play_df.late_down == True), True, False
        )
        play_df['standard_down'] = np.select(
            [
                (play_df.scrimmage_play == True) & (play_df.down_1 == True),
                (play_df.scrimmage_play == True) & (play_df.down_2 == True) & (play_df['start.distance'] < 8),
                (play_df.scrimmage_play == True) & (play_df.down_3 == True) & (play_df['start.distance'] < 5),
                (play_df.scrimmage_play == True) & (play_df.down_4 == True) & (play_df['start.distance'] < 5)
            ],
            [
                True,
                True,
                True,
                True
            ],
            default=False
        )
        play_df['passing_down'] = np.select(
            [
                (play_df.scrimmage_play == True) & (play_df.down_2 == True) & (play_df['start.distance'] >= 8),
                (play_df.scrimmage_play == True) & (play_df.down_3 == True) & (play_df['start.distance'] >= 5),
                (play_df.scrimmage_play == True) & (play_df.down_4 == True) & (play_df['start.distance'] >= 5)
            ],
            [
                True,
                True,
                True
            ],
            default=False
        )
        play_df['TFL'] = np.select(
            [
                (play_df['type.text'] != 'Penalty') & (play_df.sp == False) & (play_df.statYardage < 0),
                (play_df['sack_vec'] == True)
            ],
            [
                True,
                True
            ],
            default=False
        )
        play_df['TFL_pass'] = np.where(
            (play_df['TFL'] == True) & (play_df['pass'] == True), True, False
        )
        play_df['TFL_rush'] = np.where(
            (play_df['TFL'] == True) & (play_df['rush'] == True), True, False
        )
        play_df['havoc'] = np.where(
            (play_df['forced_fumble'] == True)|(play_df['int'] == True)|(play_df['TFL'] == True)|(play_df['pass_breakup'] == True),
            True, False
        )
        play_df['havoc_pass'] = np.where(
            (play_df['havoc'] == True) & (play_df['pass'] == True), True, False
        )
        play_df['havoc_rush'] = np.where(
            (play_df['havoc'] == True) & (play_df['rush'] == True), True, False
        )
        return play_df

    def __add_spread_time(self, play_df):
        play_df['start.pos_team_spread'] = np.where(
            (play_df["start.pos_team.id"] == play_df["homeTeamId"]), play_df['homeTeamSpread'], -1 * play_df['homeTeamSpread']
        )
        play_df['start.elapsed_share'] = ((3600 - play_df['start.adj_TimeSecsRem']) / 3600).clip(0, 3600)
        play_df['start.spread_time'] = play_df['start.pos_team_spread'] * np.exp(-4 * play_df['start.elapsed_share'])
        play_df['end.pos_team_spread'] = np.where(
            (play_df["end.pos_team.id"] == play_df["homeTeamId"]), play_df['homeTeamSpread'], -1 * play_df['homeTeamSpread']
        )
        play_df['end.pos_team_spread'] = np.where(
            (play_df["end.pos_team.id"] == play_df["homeTeamId"]), play_df['homeTeamSpread'], -1 * play_df['homeTeamSpread']
        )
        play_df['end.elapsed_share'] = ((3600 - play_df["end.adj_TimeSecsRem"]) / 3600).clip(0, 3600)
        play_df['end.spread_time'] = play_df['end.pos_team_spread'] * np.exp(-4 * play_df['end.elapsed_share'])
        return play_df

    def __calculate_ep_exp_val(self, matrix):
        return matrix[:,0] * ep_class_to_score_mapping[0] + matrix[:,1] * ep_class_to_score_mapping[1] + matrix[:,2] * ep_class_to_score_mapping[2] + matrix[:,3] * ep_class_to_score_mapping[3] + matrix[:,4] * ep_class_to_score_mapping[4] + matrix[:,5] * ep_class_to_score_mapping[5] + matrix[:,6] * ep_class_to_score_mapping[6]

    def __process_epa(self, play_df):
        play_df.loc[play_df["type.text"].isin(kickoff_vec), "down"] = 1
        play_df.loc[play_df["type.text"].isin(kickoff_vec), "start.down"] = 1
        play_df.loc[play_df["type.text"].isin(kickoff_vec), "down_1"] = True
        play_df.loc[play_df["type.text"].isin(kickoff_vec), "down_2"] = False
        play_df.loc[play_df["type.text"].isin(kickoff_vec), "down_3"] = False
        play_df.loc[play_df["type.text"].isin(kickoff_vec), "down_4"] = False
        play_df.loc[play_df["type.text"].isin(kickoff_vec), "distance"] = 10
        play_df.loc[play_df["type.text"].isin(kickoff_vec), "start.distance"] = 10
        play_df["start.yardsToEndzone.touchback"] = 99
        play_df.loc[(play_df["type.text"].isin(kickoff_vec)) & (play_df['season'] > 2013), "start.yardsToEndzone.touchback"] = 75
        play_df.loc[(play_df["type.text"].isin(kickoff_vec)) & (play_df['season'] <= 2013), "start.yardsToEndzone.touchback"] = 80

        start_touchback_data = play_df[ep_start_touchback_columns]
        start_touchback_data.columns = ep_final_names
        # self.logger.info(start_data.iloc[[36]].to_json(orient="records"))

        dtest_start_touchback = xgb.DMatrix(start_touchback_data)
        EP_start_touchback_parts = ep_model.predict(dtest_start_touchback)
        EP_start_touchback = self.__calculate_ep_exp_val(EP_start_touchback_parts)

        start_data = play_df[ep_start_columns]
        start_data.columns = ep_final_names
        # self.logger.info(start_data.iloc[[36]].to_json(orient="records"))

        dtest_start = xgb.DMatrix(start_data)
        EP_start_parts = ep_model.predict(dtest_start)
        EP_start = self.__calculate_ep_exp_val(EP_start_parts)

        play_df.loc[play_df["end.TimeSecsRem"] <= 0, "end.TimeSecsRem"] = 0
        play_df.loc[(play_df["end.TimeSecsRem"] <= 0) & (play_df.period < 5), "end.yardsToEndzone"] = 99
        play_df.loc[(play_df["end.TimeSecsRem"] <= 0) & (play_df.period < 5), "down_1_end"] = True
        play_df.loc[(play_df["end.TimeSecsRem"] <= 0) & (play_df.period < 5), "down_2_end"] = False
        play_df.loc[(play_df["end.TimeSecsRem"] <= 0) & (play_df.period < 5), "down_3_end"] = False
        play_df.loc[(play_df["end.TimeSecsRem"] <= 0) & (play_df.period < 5), "down_4_end"] = False

        play_df.loc[play_df["end.yardsToEndzone"] >= 100, "end.yardsToEndzone"] = 99
        play_df.loc[play_df["end.yardsToEndzone"] <= 0, "end.yardsToEndzone"] = 99

        play_df.loc[play_df.kickoff_tb == True, "end.yardsToEndzone"] = 75
        play_df.loc[play_df.kickoff_tb == True, "end.down"] = 1
        play_df.loc[play_df.kickoff_tb == True, "end.distance"] = 10

        play_df.loc[play_df.punt_tb == True, "end.down"] = 1
        play_df.loc[play_df.punt_tb == True, "end.distance"] = 10
        play_df.loc[play_df.punt_tb == True, "end.yardsToEndzone"] = 80

        end_data = play_df[ep_end_columns]
        end_data.columns = ep_final_names
        # self.logger.info(end_data.iloc[[36]].to_json(orient="records"))
        dtest_end = xgb.DMatrix(end_data)
        EP_end_parts = ep_model.predict(dtest_end)

        EP_end = self.__calculate_ep_exp_val(EP_end_parts)

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

            # Def 2pt conversion is its own play
            (play_df["type.text"].isin(["Defensive 2pt Conversion"])),

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
        play_df['lag_change_of_pos_team'] = play_df.change_of_pos_team.shift(1)
        play_df['lag_change_of_pos_team'] = np.where(
            play_df['lag_change_of_pos_team'].isna(), False, play_df['lag_change_of_pos_team']
        )
        play_df['EP_between'] = np.where(
            play_df.lag_change_of_pos_team == True,
            play_df['EP_start'] + play_df['lag_EP_end'],
            play_df['EP_start'] - play_df['lag_EP_end']
        )
        play_df['EP_start'] = np.where(
            (play_df["type.text"].isin(['Timeout','End Period'])) & (play_df['lag_change_of_pos_team'] == False),
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

        play_df['first_down_created'] =  np.where(
            (play_df.scrimmage_play == True) & (play_df["end.down"] == 1) & (play_df["start.pos_team.id"] == play_df["end.pos_team.id"]), True, False
        )

        play_df['EPA_success'] =  np.where(
            play_df.EPA > 0, True, False
        )
        play_df['EPA_success_early_down'] =  np.where(
            (play_df.EPA > 0) & (play_df.early_down == True), True, False
        )
        play_df['EPA_success_early_down_pass'] =  np.where(
            (play_df["pass"] == True) & (play_df.EPA > 0) & (play_df.early_down == True), True, False
        )
        play_df['EPA_success_early_down_rush'] =  np.where(
            (play_df["rush"] == True) & (play_df.EPA > 0) & (play_df.early_down == True), True, False
        )
        play_df['EPA_success_late_down'] =  np.where(
            (play_df.EPA > 0) & (play_df.late_down == True), True, False
        )
        play_df['EPA_success_late_down_pass'] =  np.where(
            (play_df["pass"] == True) & (play_df.EPA > 0) & (play_df.late_down == True), True, False
        )
        play_df['EPA_success_late_down_rush'] =  np.where(
            (play_df["rush"] == True) & (play_df.EPA > 0) & (play_df.late_down == True), True, False
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
        play_df['EPA_middle_8_success'] =  np.where(
            (play_df.EPA > 0) & (play_df["middle_8"] == True), True, False
        )
        play_df['EPA_middle_8_success_pass'] =  np.where(
            (play_df["pass"] == True) & (play_df.EPA > 0) & (play_df["middle_8"] == True), True, False
        )
        play_df['EPA_middle_8_success_rush'] =  np.where(
            (play_df["rush"] == True) & (play_df.EPA > 0) & (play_df["middle_8"] == True), True, False
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
        play_df['EPA_sp'] = np.where(
           (play_df.fg_attempt == True)|(play_df.punt == True)|(play_df.kickoff_play == True), play_df['EPA'], False 
        )
        play_df['EPA_fg'] = np.where(
           (play_df.fg_attempt == True), play_df['EPA'], None 
        )
        play_df['EPA_punt'] = np.where(
           (play_df.punt == True), play_df['EPA'], None 
        )
        play_df['EPA_kickoff'] = np.where(
           (play_df.kickoff_play == True), play_df['EPA'], None 
        )
        return play_df

    def __process_qbr__(self, play_df):
        play_df['qbr_epa'] = np.select(
            [
                (play_df.EPA < -5.0),
                (play_df.fumble_vec == True),
            ],
            [
                -5.0,
                -3.5
            ],
            default = play_df.EPA
        )

        play_df['weight'] = np.select(
            [
                (play_df.home_wp_before < .1),
                (play_df.home_wp_before >= .1) & (play_df.home_wp_before < .2),
                (play_df.home_wp_before >= .8) & (play_df.home_wp_before < .9),
                (play_df.home_wp_before > .9)
            ],
            [
                0.6,
                0.9,
                0.9,
                0.6
            ],
            default = 1
        )
        play_df['non_fumble_sack'] = (play_df['sack_vec'] == True) & (play_df['fumble_vec'] == False)

        play_df['sack_epa'] = np.where(play_df['non_fumble_sack'] == True, play_df['qbr_epa'], np.NaN)
        play_df['pass_epa'] = np.where(play_df['pass'] == True, play_df['qbr_epa'], np.NaN)
        play_df['rush_epa'] = np.where(play_df['rush'] == True, play_df['qbr_epa'], np.NaN)
        play_df['pen_epa'] = np.where(play_df['penalty_flag'] == True, play_df['qbr_epa'], np.NaN)

        play_df['sack_weight'] = np.where(play_df['non_fumble_sack'] == True, play_df['weight'], np.NaN)
        play_df['pass_weight'] = np.where(play_df['pass'] == True, play_df['weight'], np.NaN)
        play_df['rush_weight'] = np.where(play_df['rush'] == True, play_df['weight'], np.NaN)
        play_df['pen_weight'] = np.where(play_df['penalty_flag'] == True, play_df['weight'], np.NaN)

        play_df['action_play'] = (play_df.EPA != 0)
        play_df['athlete_name'] = np.select(
            [
                play_df.passer_player_name.notna(),
                play_df.rusher_player_name.notna(),
            ],
            [
                play_df.passer_player_name,
                play_df.rusher_player_name
            ],
            default=None
        )
        return play_df

    def __process_wpa(self, play_df):
        #---- prepare variables for wp_before calculations ----
        play_df['start.ExpScoreDiff_touchback'] = np.select(
            [
                (play_df["type.text"].isin(kickoff_vec))
            ],
            [
                play_df['pos_score_diff_start'] + play_df['EP_start_touchback']
            ], default = 0.000
        )
        play_df['start.ExpScoreDiff'] = np.select(
            [
                (play_df["penalty_in_text"] == True) & (play_df["type.text"] != "Penalty"),
                (play_df["type.text"] == "Timeout") & (play_df["lag_scoringPlay"] == True)
            ],
            [
                play_df['pos_score_diff_start'] + play_df['EP_start'] - play_df['EP_between'],
                (play_df["pos_score_diff_start"] + 0.92) 
            ], default = play_df['pos_score_diff_start'] + play_df.EP_start
        )
        play_df['start.ExpScoreDiff_Time_Ratio_touchback'] = play_df['start.ExpScoreDiff_touchback'] / (play_df['start.adj_TimeSecsRem'] + 1)
        play_df['start.ExpScoreDiff_Time_Ratio'] = play_df['start.ExpScoreDiff'] / (play_df['start.adj_TimeSecsRem'] + 1)

        #---- prepare variables for wp_after calculations ----
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

                play_df['pos_score_diff_end'] - play_df.EP_end,
                play_df['pos_score_diff_end'] + play_df.EP_end,
                play_df['pos_score_diff_end'] + play_df.EP_end,
                play_df['pos_score_diff_end'] + play_df.EP_end,
                play_df['pos_score_diff_end'] + 0.92,
                play_df['pos_score_diff_end'] + 0.92,
                play_df['pos_score_diff_end'] + 0.92
            ], default = play_df['pos_score_diff_end']
        )
        play_df['end.ExpScoreDiff_Time_Ratio'] = play_df['end.ExpScoreDiff'] / (play_df["end.adj_TimeSecsRem"] + 1)
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
        play_df['home_wp_before'] = np.where(play_df['start.pos_team.id'] == play_df["homeTeamId"],
                                             play_df.wp_before,
                                             play_df.def_wp_before)
        play_df['away_wp_before'] = np.where(play_df['start.pos_team.id'] != play_df["homeTeamId"],
                                             play_df.wp_before,
                                             play_df.def_wp_before)
        #---- wp_after ----
        end_data = play_df[wp_end_columns]
        end_data.columns = wp_final_names
        # self.logger.info(start_data.iloc[[36]].to_json(orient="records"))
        dtest_end = xgb.DMatrix(end_data)
        WP_end = wp_model.predict(dtest_end)
        
        play_df['lead_wp_before'] = play_df['wp_before'].shift(-1)
        play_df['lead_wp_before2'] = play_df['wp_before'].shift(-2)

        play_df['wp_after'] = WP_end
        game_complete = self.json["gameInfo"]["status"]["type"]["completed"]
        play_df['wp_after'] = np.select(
            [
                (play_df['type.text'] == "Timeout"),
                game_complete & ((play_df.lead_play_type.isna()) | (play_df.game_play_number == max(play_df.game_play_number))) & (play_df.pos_score_diff_end > 0),
                game_complete & ((play_df.lead_play_type.isna()) | (play_df.game_play_number == max(play_df.game_play_number))) & (play_df.pos_score_diff_end < 0),

                (play_df.end_of_half == 1) & (play_df['start.pos_team.id'] == play_df.lead_pos_team) & (play_df['type.text'] != "Timeout"),
                (play_df.end_of_half == 1) & (play_df['start.pos_team.id'] != play_df['end.pos_team.id']) & (play_df['type.text'] != "Timeout"),
                (play_df.end_of_half == 1) & (play_df['start.pos_team_receives_2H_kickoff'] == False) & (play_df['type.text'] == "Timeout"),

                (play_df.lead_play_type.isin(["End Period", "End of Half"])) & (play_df.change_of_pos_team == 0),
                (play_df.lead_play_type.isin(["End Period", "End of Half"])) & (play_df.change_of_pos_team == 1),

                (play_df['kickoff_onside'] == True) & (play_df['start.def_pos_team.id'] == play_df['end.pos_team.id']), # onside recovery
                (play_df['start.pos_team.id'] != play_df['end.pos_team.id'])
            ],
            [
                play_df.wp_before,
                1.0,
                0.0,

                play_df.lead_wp_before,
                (1 - play_df.lead_wp_before),
                play_df.wp_after,

                play_df.lead_wp_before,
                (1 - play_df.lead_wp_before),

                play_df.wp_after,
                (1 - play_df.wp_after)
            ],
            default = play_df.wp_after
        )

        play_df['def_wp_after']  = 1 - play_df.wp_after
        play_df['home_wp_after'] = np.where(play_df['end.pos_team.id'] == play_df["homeTeamId"],
                                             play_df.wp_after,
                                             play_df.def_wp_after)
        play_df['away_wp_after'] = np.where(play_df['end.pos_team.id'] != play_df["homeTeamId"],
                                            play_df.wp_after,
                                            play_df.def_wp_after)

        play_df['wpa'] = play_df.wp_after - play_df.wp_before        
        return play_df

    def __add_drive_data(self, play_df):
        base_groups = play_df.groupby(['drive.id'])
        play_df['drive_start'] = np.where(
            play_df['start.pos_team.id'] == play_df["homeTeamId"],
            100 - play_df["drive.start.yardLine"],
            play_df["drive.start.yardLine"]
        )
        play_df['drive_stopped'] = play_df["drive.result"].str.contains("punt|fumble|interception|downs",regex=True, case=False)
        play_df['drive_start'] = play_df['drive_start'].astype(float)
        play_df['drive_play_index'] = base_groups['scrimmage_play'].apply(lambda x: x.cumsum())
        play_df['drive_offense_plays'] = np.where((play_df['sp']==False) & (play_df['scrimmage_play'] == True), play_df['play'].astype(int), 0)
        play_df['prog_drive_EPA'] = base_groups['EPA_scrimmage'].apply(lambda x: x.cumsum())
        play_df['prog_drive_WPA'] = base_groups['wpa'].apply(lambda x: x.cumsum())
        play_df['drive_offense_yards'] = np.where((play_df['sp']==False) & (play_df['scrimmage_play'] == True), play_df['statYardage'], 0)
        play_df['drive_total_yards'] = play_df.groupby(['drive.id'])['drive_offense_yards'].apply(lambda x: x.cumsum())
        return play_df

    def create_box_score(self):
        if (self.ran_pipeline == False):
            self.run_processing_pipeline()
        # have to run the pipeline before pulling this in
        self.plays_json['completion'] = self.plays_json['completion'].astype(float)
        self.plays_json['pass_attempt'] = self.plays_json['pass_attempt'].astype(float)
        self.plays_json['target'] = self.plays_json['target'].astype(float)
        self.plays_json['yds_receiving'] = self.plays_json['yds_receiving'].astype(float)
        self.plays_json['yds_rushed'] = self.plays_json['yds_rushed'].astype(float)
        self.plays_json['rush'] = self.plays_json['rush'].astype(float)
        self.plays_json['rush_td'] = self.plays_json['rush_td'].astype(float)
        self.plays_json['pass'] = self.plays_json['pass'].astype(float)
        self.plays_json['pass_td'] = self.plays_json['pass_td'].astype(float)
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
        self.plays_json['fumble_vec'] = self.plays_json['fumble_vec'].astype(float)
        self.plays_json['sack'] = self.plays_json['sack'].astype(float)
        self.plays_json['penalty_flag'] = self.plays_json['penalty_flag'].astype(float)
        self.plays_json['play'] = self.plays_json['play'].astype(float)
        self.plays_json['scrimmage_play'] = self.plays_json['scrimmage_play'].astype(float)
        self.plays_json['sp'] = self.plays_json['sp'].astype(float)
        self.plays_json['kickoff_play'] = self.plays_json['kickoff_play'].astype(float)
        self.plays_json['punt'] = self.plays_json['punt'].astype(float)
        self.plays_json['fg_attempt'] = self.plays_json['fg_attempt'].astype(float)
        self.plays_json['EPA_penalty'] = self.plays_json['EPA_penalty'].astype(float)
        self.plays_json['EPA_sp'] = self.plays_json['EPA_sp'].astype(float)
        self.plays_json['EPA_fg'] = self.plays_json['EPA_fg'].astype(float)
        self.plays_json['EPA_punt'] = self.plays_json['EPA_punt'].astype(float)
        self.plays_json['EPA_kickoff'] = self.plays_json['EPA_kickoff'].astype(float)
        self.plays_json['TFL'] = self.plays_json['TFL'].astype(float)
        self.plays_json['TFL_pass'] = self.plays_json['TFL_pass'].astype(float)
        self.plays_json['TFL_rush'] = self.plays_json['TFL_rush'].astype(float)
        self.plays_json['havoc'] = self.plays_json['havoc'].astype(float)
        self.plays_json['havoc_pass'] = self.plays_json['havoc_pass'].astype(float)
        self.plays_json['havoc_rush'] = self.plays_json['havoc_rush'].astype(float)

        pass_box = self.plays_json[(self.plays_json["pass"] == True) & (self.plays_json.scrimmage_play == True)]
        rush_box = self.plays_json[(self.plays_json["rush"] == True) & (self.plays_json.scrimmage_play == True)]
        # pass_box.yds_receiving.fillna(0.0, inplace=True)
        passer_box = pass_box[(pass_box["pass"] == True) & (pass_box["scrimmage_play"] == True)].fillna(0.0).groupby(by=["pos_team","passer_player_name"], as_index=False).agg(
            Comp = ('completion', sum),
            Att = ('pass_attempt',sum),
            Yds = ('yds_receiving',sum),
            Pass_TD = ('pass_td', sum),
            Int = ('int', sum),
            YPA = ('yds_receiving', mean),
            EPA = ('EPA', sum),
            EPA_per_Play = ('EPA', mean),
            WPA = ('wpa', sum),
            SR = ('EPA_success', mean),
            Sck = ('sack', sum)
        ).round(2)
        passer_box = passer_box.replace({np.nan: None})
        qbs_list = passer_box.passer_player_name.to_list()

        def weighted_mean(s, df, wcol):
            s = s[s.notna() == True]
            # self.logger.info(s)
            if (len(s) == 0):
                return 0
            return np.average(s, weights=df.loc[s.index, wcol])

        pass_qbr_box = self.plays_json[(self.plays_json.athlete_name.notna() == True) & (self.plays_json.scrimmage_play == True) & (self.plays_json.athlete_name.isin(qbs_list))]
        pass_qbr = pass_qbr_box.groupby(by=["pos_team","athlete_name"], as_index=False).agg(
            qbr_epa = ('qbr_epa', partial(weighted_mean, df=pass_qbr_box, wcol='weight')),
            sack_epa = ('sack_epa', partial(weighted_mean, df=pass_qbr_box, wcol='sack_weight')),
            pass_epa = ('pass_epa', partial(weighted_mean, df=pass_qbr_box, wcol='pass_weight')),
            rush_epa = ('rush_epa', partial(weighted_mean, df=pass_qbr_box, wcol='rush_weight')),
            pen_epa = ('pen_epa', partial(weighted_mean, df=pass_qbr_box, wcol='pen_weight')),
            spread = ('start.pos_team_spread', lambda x: x.iloc[0])
        )
        # self.logger.info(pass_qbr)

        dtest_qbr = xgb.DMatrix(pass_qbr[qbr_vars])
        qbr_result = qbr_model.predict(dtest_qbr)
        pass_qbr["exp_qbr"] = qbr_result
        passer_box = pd.merge(passer_box, pass_qbr, left_on=["passer_player_name","pos_team"], right_on=["athlete_name","pos_team"])

        rusher_box = rush_box.fillna(0.0).groupby(by=["pos_team","rusher_player_name"], as_index=False).agg(
            Car= ('rush', sum),
            Yds= ('yds_rushed',sum),
            Rush_TD = ('rush_td',sum),
            YPC= ('yds_rushed', mean),
            EPA= ('EPA', sum),
            EPA_per_Play= ('EPA', mean),
            WPA= ('wpa', sum),
            SR = ('EPA_success', mean),
            Fum = ('fumble_vec', sum),
            Fum_Lost = ('fumble_lost', sum)
        ).round(2)
        rusher_box = rusher_box.replace({np.nan: None})

        receiver_box = pass_box.groupby(by=["pos_team","receiver_player_name"], as_index=False).agg(
            Rec= ('completion', sum),
            Tar= ('target',sum),
            Yds= ('yds_receiving',sum),
            Rec_TD = ('pass_td', sum),
            YPT= ('yds_receiving', mean),
            EPA= ('EPA', sum),
            EPA_per_Play= ('EPA', mean),
            WPA= ('wpa', sum),
            SR = ('EPA_success', mean),
            Fum = ('fumble_vec', sum),
            Fum_Lost = ('fumble_lost', sum)
        ).round(2)
        receiver_box = receiver_box.replace({np.nan: None})

        team_base_box = self.plays_json.groupby(by=["pos_team"], as_index=False).agg(
            EPA_plays = ('play', sum),
            total_yards = ('statYardage', sum),
            EPA_overall_total = ('EPA', sum),
        ).round(2)

        team_pen_box = self.plays_json[(self.plays_json.penalty_flag == True)].groupby(by=["pos_team"], as_index=False).agg(
            total_pen_yards = ('statYardage', sum),
            EPA_penalty = ('EPA_penalty', sum),
        ).round(2)

        team_scrimmage_box = self.plays_json[(self.plays_json.scrimmage_play == True)].groupby(by=["pos_team"], as_index=False).agg(
            scrimmage_plays = ('scrimmage_play', sum),
            EPA_overall_off = ('EPA', sum),
            EPA_overall_offense = ('EPA', sum),
            EPA_per_play = ('EPA', mean),
            EPA_explosive = ('EPA_explosive', sum),
            EPA_explosive_rate = ('EPA_explosive', mean),
            passes_rate = ('pass', mean),
            off_yards = ('statYardage', sum),
            total_off_yards = ('statYardage', sum),
            yards_per_play = ('statYardage', mean)
        ).round(2)

        team_sp_box = self.plays_json[(self.plays_json.sp == True)].groupby(by=["pos_team"], as_index=False).agg(
            special_teams_plays = ('sp', sum),
            EPA_sp = ('EPA_sp', sum),
            EPA_special_teams = ('EPA_sp', sum),
            EPA_fg = ('EPA_fg', sum),
            EPA_punt = ('EPA_punt', sum),
            kickoff_plays = ('kickoff_play', sum),
            EPA_kickoff = ('EPA_kickoff', sum)
        ).round(2)

        team_scrimmage_box_pass = self.plays_json[(self.plays_json["pass"] == True) & (self.plays_json["scrimmage_play"] == True)].fillna(0).groupby(by=["pos_team"], as_index=False).agg(
            passes = ('pass', sum),
            pass_yards = ('yds_receiving', sum),
            yards_per_pass = ('yds_receiving', mean),
            EPA_passing_overall = ('EPA', sum),
            EPA_passing_per_play = ('EPA', mean),
            EPA_explosive_passing = ('EPA_explosive', sum),
            EPA_explosive_passing_rate = ('EPA_explosive', mean),
        ).round(2)

        team_scrimmage_box_rush = self.plays_json[(self.plays_json["rush"] == True) & (self.plays_json["scrimmage_play"] == True)].groupby(by=["pos_team"], as_index=False).agg(
            EPA_rushing_overall = ('EPA', sum),
            EPA_rushing_per_play = ('EPA', mean),
            EPA_explosive_rushing = ('EPA_explosive', sum),
            EPA_explosive_rushing_rate = ('EPA_explosive', mean),
            rushes = ('rush', sum),
            rush_yards = ('yds_rushed', sum),
            yards_per_rush = ('yds_rushed', mean),
            rushing_power_rate = ('power_rush_attempt', mean),
        ).round(2)

        team_rush_base_box = self.plays_json[(self.plays_json["scrimmage_play"] == True)].groupby(by=["pos_team"], as_index=False).agg(
            rushes_rate = ('rush', mean),
            first_downs_created = ('first_down_created', sum),
            first_downs_created_rate = ('first_down_created', mean)
        )
        team_rush_power_box = self.plays_json[(self.plays_json["power_rush_attempt"] == True)].groupby(by=["pos_team"], as_index=False).agg(
            EPA_rushing_power = ('EPA', sum),
            EPA_rushing_power_per_play = ('EPA', mean),
            rushing_power_success = ('power_rush_success', sum),
            rushing_power_success_rate = ('power_rush_success', mean),
            rushing_power = ('power_rush_attempt', sum),
        )

        self.plays_json.opp_highlight_yards = self.plays_json.opp_highlight_yards.astype(float)
        self.plays_json.highlight_yards = self.plays_json.highlight_yards.astype(float)
        self.plays_json.line_yards = self.plays_json.line_yards.astype(float)
        self.plays_json.second_level_yards = self.plays_json.second_level_yards.astype(float)
        self.plays_json.open_field_yards = self.plays_json.open_field_yards.astype(float)
        team_rush_box = self.plays_json[(self.plays_json["rush"] == True) & (self.plays_json["scrimmage_play"] == True)].fillna(0).groupby(by=["pos_team"], as_index=False).agg(
            rushing_stuff = ('stuffed_run', sum),
            rushing_stuff_rate = ('stuffed_run', mean),
            rushing_stopped = ('stopped_run', sum),
            rushing_stopped_rate = ('stopped_run', mean),
            rushing_opportunity = ('opportunity_run', sum),
            rushing_opportunity_rate = ('opportunity_run', mean),
            rushing_highlight = ('highlight_run', sum),
            rushing_highlight_rate = ('highlight_run', mean),
            rushing_highlight_yards = ('highlight_yards', sum),
            line_yards = ('line_yards', sum),
            line_yards_per_carry = ('line_yards', mean),
            second_level_yards = ('second_level_yards', sum),
            open_field_yards = ('open_field_yards', sum)
        ).round(2)

        team_rush_opp_box = self.plays_json[(self.plays_json["rush"] == True) & (self.plays_json["scrimmage_play"] == True) & (self.plays_json.opportunity_run == True)].fillna(0).groupby(by=["pos_team"], as_index=False).agg(
            rushing_highlight_yards_per_opp = ('opp_highlight_yards', mean),
        ).round(2)

        team_data_frames = [team_rush_opp_box, team_pen_box, team_sp_box, team_scrimmage_box_rush, team_scrimmage_box_pass, team_scrimmage_box, team_base_box, team_rush_base_box, team_rush_power_box, team_rush_box]
        team_box = reduce(lambda left,right: pd.merge(left,right,on=['pos_team'], how='outer'), team_data_frames)
        team_box = team_box.replace({np.nan:None})

        situation_box_normal = self.plays_json[(self.plays_json.scrimmage_play == True)].groupby(by=["pos_team"], as_index=False).agg(
            EPA_success = ('EPA_success', sum),
            EPA_success_rate = ('EPA_success', mean),
        )

        situation_box_pass = self.plays_json[(self.plays_json["pass"] == True) & (self.plays_json.scrimmage_play == True)].groupby(by=["pos_team"], as_index=False).agg(
            EPA_success_pass = ('EPA_success', sum),
            EPA_success_pass_rate = ('EPA_success', mean),
        )

        situation_box_rush = self.plays_json[(self.plays_json["rush"] == True) & (self.plays_json.scrimmage_play == True)].groupby(by=["pos_team"], as_index=False).agg(
            EPA_success_rush = ('EPA_success', sum),
            EPA_success_rush_rate = ('EPA_success', mean),
        )

        situation_box_middle8 = self.plays_json[(self.plays_json["middle_8"] == True) & (self.plays_json.scrimmage_play == True)].groupby(by=["pos_team"], as_index=False).agg(
            middle_8 = ('middle_8', sum),
            middle_8_pass_rate = ('pass', mean),
            middle_8_rush_rate = ('rush', mean),
            EPA_middle_8 = ('EPA', sum),
            EPA_middle_8_per_play = ('EPA', mean),
            EPA_middle_8_success = ('EPA_success', sum),
            EPA_middle_8_success_rate = ('EPA_success', mean),
        )

        situation_box_middle8_pass = self.plays_json[(self.plays_json["pass"] == True) & (self.plays_json["middle_8"] == True) & (self.plays_json.scrimmage_play == True)].groupby(by=["pos_team"], as_index=False).agg(
            middle_8_pass = ('pass', sum),
            EPA_middle_8_pass = ('EPA', sum),
            EPA_middle_8_pass_per_play = ('EPA', mean),
            EPA_middle_8_success_pass = ('EPA_success', sum),
            EPA_middle_8_success_pass_rate = ('EPA_success', mean),
        )

        situation_box_middle8_rush = self.plays_json[(self.plays_json["rush"] == True) & (self.plays_json["middle_8"] == True) & (self.plays_json.scrimmage_play == True)].groupby(by=["pos_team"], as_index=False).agg(
            middle_8_rush = ('rush', sum),

            EPA_middle_8_rush = ('EPA', sum),
            EPA_middle_8_rush_per_play = ('EPA', mean),

            EPA_middle_8_success_rush = ('EPA_success', sum),
            EPA_middle_8_success_rush_rate = ('EPA_success', mean),
        )

        situation_box_early = self.plays_json[(self.plays_json.early_down == True)].groupby(by=["pos_team"], as_index=False).agg(
            EPA_success_early_down = ('EPA_success', sum),
            EPA_success_early_down_rate = ('EPA_success', mean),
            early_downs = ('early_down', sum),
            early_down_pass_rate = ('pass', mean),
            early_down_rush_rate = ('rush', mean),
            EPA_early_down = ('EPA', sum),
            EPA_early_down_per_play = ('EPA', mean),
            early_down_first_down = ('first_down_created', sum),
            early_down_first_down_rate = ('first_down_created', mean)
        )

        situation_box_early_pass = self.plays_json[(self.plays_json["pass"] == True) & (self.plays_json.early_down == True)].groupby(by=["pos_team"], as_index=False).agg(
            early_down_pass = ('pass', sum),
            EPA_early_down_pass = ('EPA', sum),
            EPA_early_down_pass_per_play = ('EPA', mean),
            EPA_success_early_down_pass = ('EPA_success', sum),
            EPA_success_early_down_pass_rate = ('EPA_success', mean),
        )

        situation_box_early_rush = self.plays_json[(self.plays_json["rush"] == True) & (self.plays_json.early_down == True)].groupby(by=["pos_team"], as_index=False).agg(
            early_down_rush = ('rush', sum),
            EPA_early_down_rush = ('EPA', sum),
            EPA_early_down_rush_per_play = ('EPA', mean),
            EPA_success_early_down_rush = ('EPA_success', sum),
            EPA_success_early_down_rush_rate = ('EPA_success', mean),
        )

        situation_box_late = self.plays_json[(self.plays_json.late_down == True)].groupby(by=["pos_team"], as_index=False).agg(
            EPA_success_late_down = ('EPA_success_late_down', sum),
            EPA_success_late_down_pass = ('EPA_success_late_down_pass', sum),
            EPA_success_late_down_rush = ('EPA_success_late_down_rush', sum),
            late_downs = ('late_down', sum),
            late_down_pass = ('late_down_pass', sum),
            late_down_rush = ('late_down_rush', sum),
            EPA_late_down = ('EPA', sum),
            EPA_late_down_per_play = ('EPA', mean),
            EPA_success_late_down_rate = ('EPA_success_late_down', mean),
            EPA_success_late_down_pass_rate = ('EPA_success_late_down_pass', mean),
            EPA_success_late_down_rush_rate = ('EPA_success_late_down_rush', mean),
            late_down_pass_rate = ('late_down_pass', mean),
            late_down_rush_rate = ('late_down_rush', mean)
        )

        situation_box_standard = self.plays_json[self.plays_json.standard_down == True].groupby(by=["pos_team"], as_index=False).agg(
            EPA_success_standard_down = ('EPA_success_standard_down', sum),
            EPA_success_standard_down_rate = ('EPA_success_standard_down', mean),
            EPA_standard_down = ('EPA_success_standard_down', sum),
            EPA_standard_down_per_play = ('EPA_success_standard_down', mean)
        )
        situation_box_passing = self.plays_json[self.plays_json.passing_down == True].groupby(by=["pos_team"], as_index=False).agg(
            EPA_success_passing_down = ('EPA_success_passing_down', sum),
            EPA_success_passing_down_rate = ('EPA_success_passing_down', mean),
            EPA_passing_down = ('EPA_success_standard_down', sum),
            EPA_passing_down_per_play = ('EPA_success_standard_down', mean)
        )
        situation_data_frames = [situation_box_normal, situation_box_pass, situation_box_rush, situation_box_early, situation_box_early_pass, situation_box_early_rush, situation_box_middle8, situation_box_middle8_pass, situation_box_middle8_rush, situation_box_late, situation_box_standard, situation_box_passing]
        situation_box = reduce(lambda left,right: pd.merge(left,right,on=['pos_team'], how='outer'), situation_data_frames)
        situation_box = situation_box.replace({np.nan:None})

        self.plays_json.drive_stopped = self.plays_json.drive_stopped.astype(float)
        def_base_box = self.plays_json[(self.plays_json.scrimmage_play == True)].groupby(by=["def_pos_team"], as_index=False).agg(
            scrimmage_plays = ('scrimmage_play', sum),
            TFL = ('TFL', sum),
            TFL_pass = ('TFL_pass', sum),
            TFL_rush = ('TFL_rush', sum),
            havoc_total = ('havoc', sum),
            havoc_total_rate = ('havoc', mean),
            fumbles = ('fumble_vec', sum),
            def_int = ('int', sum),
            drive_stopped_rate = ('drive_stopped', mean)
        )
        def_base_box.drive_stopped_rate = 100 * def_base_box.drive_stopped_rate
        def_base_box = def_base_box.replace({np.nan:None})

        def_box_havoc_pass = self.plays_json[(self.plays_json.scrimmage_play == True) & (self.plays_json["pass"] == True)].groupby(by=["def_pos_team"], as_index=False).agg(
            havoc_total_pass = ('havoc', sum),
            havoc_total_pass_rate = ('havoc', mean),
            sacks = ('sack', sum),
            sacks_rate = ('sack', mean),
        )
        def_box_havoc_pass = def_box_havoc_pass.replace({np.nan:None})

        def_box_havoc_rush = self.plays_json[(self.plays_json.scrimmage_play == True) & (self.plays_json["rush"] == True)].groupby(by=["def_pos_team"], as_index=False).agg(
            havoc_total_rush = ('havoc', sum),
            havoc_total_rush_rate = ('havoc', mean),
        )
        def_box_havoc_rush = def_box_havoc_rush.replace({np.nan:None})

        def_data_frames = [def_base_box,def_box_havoc_pass,def_box_havoc_rush]
        def_box = reduce(lambda left,right: pd.merge(left,right,on=['def_pos_team'], how='outer'), def_data_frames)
        def_box = def_box.replace({np.nan:None})
        def_box_json = json.loads(def_box.to_json(orient="records"))

        turnover_box = self.plays_json[(self.plays_json.scrimmage_play == True)].groupby(by=["pos_team"], as_index=False).agg(
            fumbles_lost = ('fumble_lost', sum),
            fumbles_recovered = ('fumble_recovered', sum),
            total_fumbles = ('fumble_vec', sum),
            Int = ('int', sum),
        ).round(2)
        turnover_box = turnover_box.replace({np.nan:None})
        turnover_box_json = json.loads(turnover_box.to_json(orient="records"))
        if (len(turnover_box_json) < 2):
            for i in range(len(turnover_box_json), 2):
                turnover_box_json.append({})

        team_def_box = self.json["boxscore"]["players"]
        for (idx, team) in enumerate(team_def_box):
            def_box_stats_search = list(filter(lambda x: "defensive" in x["name"], team["statistics"]))
            if (len(def_box_stats_search) > 0):
                def_box_stats = def_box_stats_search[0]
                zipped_def_box_stat = zip(def_box_stats["labels"], def_box_stats["totals"])
                # away first, home second
                for (label, total) in zipped_def_box_stat:
                    turnover_box_json[idx][label] = round(float(total), 2)
                    def_box_json[idx][label] = round(float(total), 2)

        total_fumbles = reduce(lambda x, y: x+y, map(lambda x: (x["total_fumbles"] if ("total_fumbles" in x.keys()) else 0), turnover_box_json))

        away_passes_def = turnover_box_json[1]["PD"] if ("PD" in turnover_box_json[1].keys()) else 0
        away_passes_int = turnover_box_json[0]["Int"] if ("Int" in turnover_box_json[0].keys()) else 0
        turnover_box_json[0]["expected_turnovers"] = (0.5 * total_fumbles) + (0.22 * (away_passes_def + away_passes_int))

        home_passes_def = turnover_box_json[0]["PD"] if ("PD" in turnover_box_json[0].keys()) else 0
        home_passes_int = turnover_box_json[1]["Int"] if ("Int" in turnover_box_json[1].keys()) else 0
        turnover_box_json[1]["expected_turnovers"] = (0.5 * total_fumbles) + (0.22 * (home_passes_def + home_passes_int))

        turnover_box_json[0]["Int"] = int(turnover_box_json[0]["Int"])
        turnover_box_json[1]["Int"] = int(turnover_box_json[1]["Int"])

        turnover_box_json[0]["expected_turnover_margin"] = turnover_box_json[1]["expected_turnovers"] - turnover_box_json[0]["expected_turnovers"]
        turnover_box_json[1]["expected_turnover_margin"] = turnover_box_json[0]["expected_turnovers"] - turnover_box_json[1]["expected_turnovers"]

        away_to = turnover_box_json[0]["fumbles_lost"] + turnover_box_json[0]["Int"]
        home_to = turnover_box_json[1]["fumbles_lost"] + turnover_box_json[1]["Int"]

        turnover_box_json[0]["turnovers"] = away_to
        turnover_box_json[1]["turnovers"] = home_to

        turnover_box_json[0]["turnover_margin"] = home_to - away_to
        turnover_box_json[1]["turnover_margin"] = away_to - home_to

        turnover_box_json[0]["turnover_luck"] = 5.0 * (turnover_box_json[0]["turnover_margin"] - turnover_box_json[0]["expected_turnover_margin"])
        turnover_box_json[1]["turnover_luck"] = 5.0 * (turnover_box_json[1]["turnover_margin"] - turnover_box_json[1]["expected_turnover_margin"])

        self.plays_json.drive_start = self.plays_json.drive_start.astype(float)
        drives_data = self.plays_json[(self.plays_json.scrimmage_play == True)].groupby(by=["pos_team"], as_index=False).agg(
            drive_total_available_yards = ('drive_start', sum),
            drive_total_gained_yards = ('drive.yards', sum),
            avg_field_position = ('drive_start', mean),
            plays_per_drive = ('drive.offensivePlays', mean),
            yards_per_drive = ('drive.yards', mean),
            drives = ('drive.id', pd.Series.nunique)
        )
        drives_data['drive_total_gained_yards_rate'] = (100 * drives_data.drive_total_gained_yards / drives_data.drive_total_available_yards).round(2)

        return {
            "pass" : json.loads(passer_box.to_json(orient="records")),
            "rush" : json.loads(rusher_box.to_json(orient="records")),
            "receiver" : json.loads(receiver_box.to_json(orient="records")),
            "team" : json.loads(team_box.to_json(orient="records")),
            "situational" : json.loads(situation_box.to_json(orient="records")),
            "defensive" : def_box_json,
            "turnover" : turnover_box_json,
            "drives" : json.loads(drives_data.to_json(orient="records"))
        }

    def run_processing_pipeline(self):
        if (self.ran_pipeline == False):
            self.plays_json = self.__add_downs_data(self.plays_json)
            self.plays_json = self.__add_play_type_flags(self.plays_json)
            self.plays_json = self.__add_rush_pass_flags(self.plays_json)
            self.plays_json = self.__add_team_score_variables(self.plays_json)
            self.plays_json = self.__add_new_play_types(self.plays_json)
            self.plays_json = self.__setup_penalty_data(self.plays_json)
            self.plays_json = self.__add_play_category_flags(self.plays_json)
            self.plays_json = self.__add_yardage_cols(self.plays_json)
            self.plays_json = self.__add_player_cols(self.plays_json)
            self.plays_json = self.__after_cols(self.plays_json)
            self.plays_json = self.__add_spread_time(self.plays_json)
            self.plays_json = self.__process_epa(self.plays_json)
            self.plays_json = self.__process_wpa(self.plays_json)
            self.plays_json = self.__add_drive_data(self.plays_json)
            self.plays_json = self.__process_qbr__(self.plays_json)
            self.plays_json = self.plays_json.replace({np.nan: None})
            self.ran_pipeline = True
        return self.plays_json