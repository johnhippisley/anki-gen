import json
import sqlite3
from dataclasses import dataclass
from utils.anki import AnkiCard
from pypinyin.contrib.tone_convert import to_tone
import re

## String formatting functions ##
wrap_bf = lambda s, target: s.replace(target, f"<b>{target}</b>")

def pretty_pinyin(s: str) -> str:
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

	return to_tone(s)

# Database configuration struct
@dataclass
class DatabaseConfig:
	db_file: str
	db_name: str
	condition: str
	fields: dict[str, list[str]]  	# DB field -> list of Anki fields it should be applied to
	bwrap_fields: list[str]			# Fields where we should replace seed with '<b>seed</b>'
	pinyin_fields: list[str]		# Fields where Pinyin will be included
	
	# Returns dict of type [Anki field -> contents]
	def query(self, seed: str, verbose: int = 0) -> dict[str, str]: 
		with sqlite3.connect(self.db_file) as conn:
			cols = ",".join(self.fields.keys())
			cond_repl = self.condition.replace("{{seed}}", seed)
			full_query = f"SELECT {cols} FROM {self.db_name} WHERE {cond_repl};"
			
			cur = conn.cursor()
			if verbose == 2:
				print(f"Querying {self.db_file} => '{full_query}'")
			cur.execute(full_query)
			row = cur.fetchone()
			if row is None: return {}
			anki_fields: dict[str, str] = {}

			for db_field, value in zip(self.fields.keys(), row):
				if db_field in self.pinyin_fields: 
					value = pretty_pinyin(value)
				elif db_field in self.bwrap_fields:
					value = wrap_bf(value, seed)
				for anki_field in self.fields[db_field]:
					anki_fields[anki_field] = value
			return anki_fields

@dataclass
class Configuration:
	db_configs: list[DatabaseConfig]
	anki_seed_field: str
	anki_seed_field_extra: list[str]

def get_configuration(json_path: str) -> Configuration:
	with open(json_path, "r", encoding="utf-8") as f:
		data = json.load(f)

	db_configs: list[DatabaseConfig] = []
	anki_seed_field = ""
	anki_seed_field_extra = []

	for key, db_info in data.items():
		if key == "config":
			anki_seed_field = db_info["anki_seed_field"]
			anki_seed_field_extra = db_info.get("anki_seed_field_extra", [])
			continue

		fields: dict[str, list[str]] = {}

		for db_field, anki_fields in db_info["fields"].items():
			if isinstance(anki_fields, str):
				fields[db_field] = [anki_fields]
			else:
				fields[db_field] = anki_fields

		db_configs.append(
			DatabaseConfig(
				db_file=key,
				db_name=db_info["name"],
				condition=db_info["condition"],
				fields=fields,
				bwrap_fields=db_info.get("bwrap_fields", []),
				pinyin_fields=db_info.get("pinyin_fields", [])
			)
		)

	return Configuration(
		db_configs=db_configs,
		anki_seed_field=anki_seed_field,
		anki_seed_field_extra=anki_seed_field_extra
	)

def gen_anki_card(config: Configuration, seed: str, model_name: str, tags: list = [], verbose: int = 0):
	card = AnkiCard(model_name=model_name)

	for db in config.db_configs:
		fields = db.query(seed, verbose)
		for field_name, contents in fields.items():
			if field_name is not config.anki_seed_field:
				card.add_field(field_name, contents)
	for tag in tags:
		card.add_tag(tag)

	if not card.fields:
		return None

	for seed_field in config.anki_seed_field_extra + [config.anki_seed_field]:
		card.add_field(seed_field, seed, top=True)
	return card