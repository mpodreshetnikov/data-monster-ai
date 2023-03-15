import dataframe_image as dfi
from pandas import DataFrame, concat
import logging


logger = logging.getLogger(__name__)


def save_table_image_to_file(data: DataFrame, filename: str) -> None:
    MAX_ROWS = 100
    # take only MAX_ROWS-1 rows if more for not big image reason
    if len(data.index) > MAX_ROWS:
        info_text = f"{len(data.index)} rows but {MAX_ROWS} may be printed"
        data = data.head(MAX_ROWS - 1)
        info_row = DataFrame([info_text]+['...']*(len(data.columns)-1), index=data.columns)
        data = concat([data, info_row.transpose()])

    dfi.export(data, filename, table_conversion="matplotlib")