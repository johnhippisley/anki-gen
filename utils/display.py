import re
import shutil
from wcwidth import wcswidth
from enum import StrEnum

class CC(StrEnum):
	BOLD = "\033[1m"
	ITALIC = "\033[3m"
	RESET = "\033[0m"
	GREEN = "\033[32m"
	RED = "\033[31m"
	BG_RED = "\033[41m"
	BG_GREEN = "\033[42m"
	BG_YELLOW = "\033[43m"
	BG_BLUE = "\033[44m"
	BG_MAGENTA = "\033[45m"
	BG_CYAN = "\033[46m"
	BG_WHITE = "\033[47m"
	BG_GRAY = "\033[100m"

def strip_ansi(s: str) -> str:
	return re.sub(r"\033\[[0-9;]*m", "", s)

def display_len(s: str) -> int:
	return max(0, wcswidth(strip_ansi(s)))

def html_bold_to_ansi(s: str) -> str:
	s = re.sub(r"<b>(.*?)</b>", rf"{CC.BOLD}\1{CC.RESET}", s)
	s = re.sub(r"<strong>(.*?)</strong>", rf"{CC.BOLD}\1{CC.RESET}", s)
	return s

def is_cjk(ch: str) -> bool:
	return (
		"\u4e00" <= ch <= "\u9fff" or
		"\u3400" <= ch <= "\u4dbf" or
		"\uf900" <= ch <= "\ufaff"
	)

def tokenize_display_text(s: str) -> list[str]:
	ret: list[str] = []
	buf = ""
	for ch in s:
		if ch.isspace():
			if buf:
				ret.append(buf)
				buf = ""
			ret.append(" ")
		elif is_cjk(ch):
			if buf:
				ret.append(buf)
				buf = ""
			ret.append(ch)
		else:
			buf += ch
	if buf:
		ret.append(buf)
	return ret

def wrap_text(s: str, max_len: int) -> list[str]:
	lines: list[str] = []
	cur = ""
	for tok in tokenize_display_text(s):
		if tok == " ":
			if cur and not cur.endswith(" "):
				cur += " "
			continue

		candidate = cur + tok
		if display_len(candidate) <= max_len:
			cur = candidate
		else:
			if cur:
				lines.append(cur.rstrip())
				cur = tok.lstrip()
			else:
				part = ""
				for ch in tok:
					if display_len(part + ch) > max_len:
						lines.append(part)
						part = ch
					else:
						part += ch
				cur = part
	if cur:
		lines.append(cur.rstrip())
	return lines or [""]

def terminal_box_width(max_width: int = 90, min_width: int = 50) -> int:
	term_width = shutil.get_terminal_size((max_width, 20)).columns
	return max(min_width, min(max_width, term_width))

def box_row(text: str, inner_width: int) -> str:
	pad = max(0, inner_width - display_len(text))
	return f"│ {text}{' ' * pad} │"

def format_field_rows(name: str, value: str, inner_width: int) -> list[str]:
	value = html_bold_to_ansi(str(value).replace("\n", "\\n"))
	prefix = f"{CC.GREEN}{CC.BOLD}{name}:{CC.RESET} "
	continuation_prefix = " " * display_len(prefix)
	first_width = inner_width - display_len(prefix)
	wrapped = wrap_text(value, first_width)
	rows = [box_row(prefix + wrapped[0], inner_width)]

	for extra in wrapped[1:]:
		rows.append(box_row(continuation_prefix + extra, inner_width))

	return rows