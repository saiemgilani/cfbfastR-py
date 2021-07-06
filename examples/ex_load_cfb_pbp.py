import cfbfastR
def main():
    cfb_df = cfbfastR.cfb.load_cfb_pbp(seasons=range(2011,2021))
    print(cfb_df.head())
    nfl_df = cfbfastR.nfl.load_nfl_pbp(seasons=range(2011,2021))
    print(nfl_df.head())

if __name__ == "__main__":
    main()