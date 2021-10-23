from cfbfastR.cfb import PlayProcess
import pandas as pd

def test_basic_pbp():
    test = PlayProcess(gameId = 401301025)
    test.cfb_pbp()
    assert test.json != None

    test.run_processing_pipeline()
    assert len(test.plays_json) > 0
    assert test.ran_pipeline == True
    assert isinstance(test.plays_json, pd.DataFrame)