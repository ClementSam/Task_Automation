def parse_bool_strict(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    if isinstance(v, str):
        s = v.strip().lower()
        if s in {"true","1","yes","y","on"}:
            return True
        if s in {"false","0","no","n","off"}:
            return False
    return None  # indéterminé
