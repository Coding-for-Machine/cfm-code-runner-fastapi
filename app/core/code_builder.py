
def build_final_code(user_code: str, top: str | None, bottom: str | None) -> str:
    parts = []
    if top:
        parts.append(top.strip())
    parts.append(user_code.strip())
    if bottom:
        parts.append(bottom.strip())
    return "\n\n".join(parts)
