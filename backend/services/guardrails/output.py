import re

CODE_BLOCK_PATTERN = re.compile(r"```[\s\S]*?```", re.MULTILINE)
INLINE_CODE_PATTERN = re.compile(r"`[^`]+`")
URL_PATTERN = re.compile(r"https?://[^\s\)>\]\"]+", re.IGNORECASE)
MARKDOWN_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\([^\)]+\)")


def sanitize_output(text: str) -> str:
    text = CODE_BLOCK_PATTERN.sub("", text)
    text = INLINE_CODE_PATTERN.sub("", text)
    text = MARKDOWN_LINK_PATTERN.sub(r"\1", text)
    text = URL_PATTERN.sub("[link removed]", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
