import json
import sqlite3
from dataclasses import dataclass
from utils.anki import AnkiCard
import utils.zh as zh 

# Wrap target in <b> ... </b>
wrap_bf = lambda s, target: s.replace(target, f"<b>{target}</b>")

# Invert a one-to-many dictionary
get_key = lambda d, value: next(k for k, values in d.items() if value in values)

# Checks whether or not word appears in sentence as a natural distinct word
def nlp_check_distinct(lang: str, sentence: str, word: str):
	if lang == "zh":
		return zh.word_appears(word, sentence)
	else:
		print(f"Unsupported language! '{lang}'")
		exit(-1)

# Database configuration struct
@dataclass
class DatabaseConfig:
	db_file: str
	db_name: str
	lang: str							# Database language
	condition: str						# SQL WHERE '...'
	field_map: dict[str, list[str]] 	# DB field --> list of Anki fields it should be applied to
	check_seg: list[str]				# DB fields to verify contain the seed as a distinct word

	# Returns dict of type [Anki field -> contents]
	def query(self, seed: str, verbose: int = 0) -> dict[str, str]: 
		with sqlite3.connect(self.db_file) as conn:
			cols = ",".join(self.field_map.keys())
			cond_repl = self.condition.replace("{{seed}}", seed)
			full_query = f"SELECT {cols} FROM {self.db_name} WHERE {cond_repl};"
			cur = conn.cursor()

			if verbose == 2:
				print(f"Querying {self.db_file} => '{full_query}'")

			cur.execute(full_query)
			anki_fields: dict[str, str] = {} # Actual contents of new Anki card

			# Fetch rows until we find a suitable match	
			found = False	
			while not found:
				found = True
				anki_fields = {}

				row = cur.fetchone()
				if row is not None:
					for db_field, value in zip(self.field_map.keys(), row):
						if db_field in self.check_seg:
							found = nlp_check_distinct(self.lang, sentence=value, word=seed)
							if not found:
								break

						for anki_field in self.field_map[db_field]:
							anki_fields[anki_field] = value
				else:
					found = False
					break

			if not found: return {}
			else: return anki_fields

@dataclass
class Configuration:
	db_configs: list[DatabaseConfig]
	anki_seed_field: str
	anki_seed_field_copyto: list[str]
	tts_gen: list[str]
	bwrap_fields: list[str]
	pinyin_fields: list[str]

def csv_get(contents, name, expected_type):
	if expected_type == list:
		inner = contents.get(name, [])
		if isinstance(inner, str):
			return [inner]
		return inner
	if expected_type == str:
		return contents.get(name, "")
	if expected_type == dict:
		return contents.get(name, {})
	raise ValueError(f"Unsupported expected_type: {expected_type}")

def get_configuration(json_path: str) -> Configuration:
	with open(json_path, "r", encoding="utf-8") as f:
		data = json.load(f)

	db_configs: list[DatabaseConfig] = []
	anki_seed_field: str = ""
	anki_seed_field_copyto: list[str] = []
	bwrap_fields: list[str] = []
	pinyin_fields: list[str] = []
	check_seg: list[str] = []
	tts_gen: dict[str, str] = {}

	for key, db_info in data.items():
		# Main configuration
		if key == "__config__":
			anki_seed_field = csv_get(db_info, "anki_seed_field", str)
			anki_seed_field_copyto = csv_get(db_info, "anki_seed_field_copyto", list)
			bwrap_fields = csv_get(db_info, "seed_bwrap_fields", list)
			pinyin_fields = csv_get(db_info, "pinyin_fields", list)
			check_seg = csv_get(db_info, "check_seed_distinct_word", list)
			tts_gen = csv_get(db_info, "edge_tts_generate", dict)
			continue

		# Individual database configuration
		field_map: dict[str, list[str]] = {}
		for db_field in db_info["fields"]:
			field_map[db_field] = csv_get(db_info["fields"], db_field, list)

		# List of anki fields the database interacts with
		anki_fields = [field for field_list in field_map.values() for field in field_list]

		db_configs.append(
			DatabaseConfig(
				db_file = key,
				db_name = csv_get(db_info, "name", str),
				lang = csv_get(db_info, "lang", str),
				condition = csv_get(db_info, "condition", str),
				field_map = field_map,			
				check_seg = [get_key(field_map, field) for field in check_seg if field in anki_fields]
			)
		)

	return Configuration(
		db_configs=db_configs,
		anki_seed_field=anki_seed_field,
		anki_seed_field_copyto=anki_seed_field_copyto,
		tts_gen=tts_gen,
		bwrap_fields=bwrap_fields,
		pinyin_fields = pinyin_fields,
	)

def gen_anki_card(config: Configuration, seed: str, model_name: str, tags: list = [], verbose: int = 0):
	card = AnkiCard(model_name=model_name)

	# Copy queried fields & tags into Anki card
	for db in config.db_configs:
		fields = db.query(seed, verbose)
		for field_name, contents in fields.items():
			if field_name is not config.anki_seed_field:
				# Prettify pinyin and apply bold-wrapping where specified
				if field_name in config.pinyin_fields:
					contents = zh.pretty_pinyin(contents)
				if field_name in config.bwrap_fields:
					contents = wrap_bf(contents, seed)

				card.add_field(field_name, contents)

	for tag in tags:
		card.add_tag(tag)

	if not card.fields:
		return None

	# Copy seed into additional fields if specified
	for seed_field in config.anki_seed_field_copyto + [config.anki_seed_field]:
		card.add_field(seed_field, seed, top=True)

	# Handle TTS
	#...
	return card