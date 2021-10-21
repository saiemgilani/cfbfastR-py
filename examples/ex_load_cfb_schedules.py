import cfbfastR
from cfbfastR.cfb import *

def main():
    cfb_schedules_df = cfbfastR.cfb.load_cfb_schedule(seasons=range(2011,2022))
    print(cfb_schedules_df.head())

if __name__ == "__main__":
    main()
