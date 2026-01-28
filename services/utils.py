def block(title: str, lines: list[str]) -> str:
    out = f"📦 <b>{title}</b>\n"
    out += "\n".join(lines)
    return out

def line(emoji: str, text: str) -> str:
    return f"{emoji} {text}"

def fairness_block(hash_value: str, result: str) -> str:
    return (
        "🔐 <b>Fairness Check</b>\n"
        f"SHA-256 Hash:\n<code>{hash_value}</code>\n"
        f"Result:\n<code>{result}</code>"
    )
