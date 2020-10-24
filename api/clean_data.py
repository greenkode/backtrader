import os
import pandas as pd

str_dir = '/Volumes/Seagate Expansion Drive/binance/data/1h/'
for filename in os.listdir(str_dir):
    df = pd.read_csv(os.path.join(str_dir, filename), header=[0])
    df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
    df.to_csv(os.path.join(str_dir, filename), index=False)
