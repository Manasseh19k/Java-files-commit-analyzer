import pandas as pd
import os

folder_path = r"C:\Users\fajos\Desktop\Research\pmd_csv_files"

list_of_files = os.listdir(folder_path)

csv_files = [file for file in list_of_files if file.endswith('.csv')]

df_list = []

for csv in csv_files:
    file_path = os.path.join(folder_path, csv)
    try:
        df = pd.read_csv(os.path.join(folder_path, csv))
        df_list.append(df)
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(file_path, sep='\t', encoding='utf-16')
            df_list.append(df)
        except Exception as e:
            print(f"Error reading csv file {file_path} because of error: {e}")

    except Exception as e:
        print(f"Error reading csv file {file_path} because of error: {e}")

combined_df = pd.concat(df_list, ignore_index=True)

combined_df.to_csv(os.path.join(folder_path, 'combined_csv_files.csv'), index=False)
