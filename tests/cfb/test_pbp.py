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

def test_adv_box_score():
    test = PlayProcess(gameId = 401301025)
    test.cfb_pbp()
    assert test.json != None

    test.run_processing_pipeline()
    assert len(test.plays_json) > 0
    assert test.ran_pipeline == True
    assert isinstance(test.plays_json, pd.DataFrame)

    box = test.create_box_score()
    assert box != None
    assert len(set(box.keys()).difference({"pass","team","situational","receiver","rush","receiver","defensive","turnover","drives"})) == 0