import json_fix, json
from pandas import DataFrame

def fix_serialiazing():
    ext_types_to_fix = [DataFrame]

    json_fix.fix_it()
    checkers = map(lambda type: lambda obj: isinstance(obj, type), ext_types_to_fix)
    for checker in checkers:
        json.override_table[checker] = lambda obj_of_that_class: json.loads(obj_of_that_class.to_json())