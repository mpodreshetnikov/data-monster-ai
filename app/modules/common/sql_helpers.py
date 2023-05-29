import re


def update_limit(sql_script: str, new_limit: int, limit_str = "LIMIT") -> str | None:
    """Update the limit in the SQL script."""
    if new_limit <= 0:
        raise ValueError("Limit must be greater than 0")
    if not sql_script or len(sql_script) == 0:
        return None
    # check if limit is already in the script
    if re.search(f"{limit_str}\s+\d+", sql_script, re.IGNORECASE):
        # replace the limit
        return re.sub(f"{limit_str}\s+\d+", f"{limit_str} {new_limit}", sql_script, flags=re.IGNORECASE)
    # add the limit if it is not in the script
    return f"{sql_script}\n{limit_str} {new_limit}"