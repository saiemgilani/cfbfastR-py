import cfbfastR
def main():
    cfb_df = cfbfastR.cfb.load_cfb_pbp(seasons=range(2003,2021))
    cfb_df.head()


if __name__ == "__main__":
    main()