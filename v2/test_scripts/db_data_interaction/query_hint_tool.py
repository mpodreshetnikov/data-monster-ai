from typing import List, Tuple
import yaml

from langchain.agents.agent_toolkits.base import BaseToolkit
from langchain.tools.json.tool import JsonSpec
from langchain.agents.agent_toolkits import JsonToolkit


def get_query_hint_toolkit(json_path: str) -> BaseToolkit:
    with open(json_path, "r", encoding="utf-8") as f:
        data = yaml.load(f, Loader=yaml.FullLoader)
    
    json_spec = JsonSpec(dict_= data, max_value_length=500)
    json_toolkit = JsonToolkit(spec=json_spec)
    return json_toolkit
