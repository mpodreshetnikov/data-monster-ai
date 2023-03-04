import pandas as pd, dataframe_image as dfi

def draw_table(db_response_df, filename):
    dfi.export(db_response_df, filename, table_conversion="matplotlib")