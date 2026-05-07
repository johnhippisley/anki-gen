import re
from pypinyin.contrib.tone_convert import to_tone
from utils.display import CC

# Formats pinyin and converts to tone-marks if necessary (e.g. ni3 hao3 to nǐ hǎo)
_pypinyin = None
def pretty_pinyin(s: str) -> str:
	global _pypinyin

	if _pypinyin is None:
		print(f"{CC.BOLD}[Loading PyPinyin...]{CC.RESET}")
		import pypinyin.contrib.tone_convert as tone_convert
		_pypinyin = tone_convert

	punct_map = {"，": ",", "。": ".", "？": "?", "！": "!", "；": ";", "：": ":", "“": '"', "”": '"', "「": '"', 
				 "」": '"', "『": '"', "』": '"', "‘": "'", "’": "'", "（": "(", "）": ")", "【": "[", "】": "]"}

	for old, new in punct_map.items():
		s = s.replace(old, new)

	s = re.sub(r"\s+", " ", s).strip()
	s = re.sub(r"\s+([,.!?;:)\]])", r"\1", s)
	s = re.sub(r"([([{])\s+", r"\1", s)
	s = re.sub(r"([,.!?;:])(?=[A-Za-z0-9āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜüÜ])", r"\1 ", s)

	out, in_quote = [], False
	for ch in s:
		if ch == '"':
			if in_quote:
				while out and out[-1] == " ":
					out.pop()
				out.append('"')
				in_quote = False
			else:
				if out and out[-1] not in " ([{":
					out.append(" ")
				out.append('"')
				in_quote = True
		else:
			out.append(ch)

	s = "".join(out)
	s = re.sub(r'"\s+', '"', s)
	s = re.sub(r"\s+", " ", s).strip()

	return _pypinyin.to_tone(s)

# Lazy Jieba wrapper for word segmentation
_jieba = None
def word_appears(word: str, sentence: str) -> bool:
	global _jieba

	if _jieba is None:
		print(f"{CC.BOLD}[Loading Jieba...]{CC.RESET}")
		import jieba
		_jieba = jieba

	return word in _jieba.lcut(sentence)