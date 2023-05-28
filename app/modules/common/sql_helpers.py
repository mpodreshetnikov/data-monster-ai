import re


def update_limit(sql_script: str, new_limit: int, limit_str = "LIMIT") -> str:
    """Update the limit in the SQL script."""
    if new_limit <= 0:
        raise ValueError("Limit must be greater than 0")
    if sql_script is None or len(sql_script) == 0:
        return None
    if re.search(f"{limit_str}\s+\d+", sql_script, re.IGNORECASE):
        return re.sub(f"{limit_str}\s+\d+", f"{limit_str} {new_limit}", sql_script, flags=re.IGNORECASE)
    else:
        return f"{sql_script}\n{limit_str} {new_limit}"