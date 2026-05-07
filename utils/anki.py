import sys
import csv
import json
import urllib.request
from dataclasses import dataclass, field
from utils.display import *

CONNECT_URL = "http://127.0.0.1:8765"
LOG_FILE = "connect.log"

def log_a(msg: str):
	print(msg)
	with open(LOG_FILE, "a", encoding="utf-8") as f:
		f.write(msg + "\n")

# Wrapper for AnkiConnect
def invoke(action, **params):
	req = urllib.request.Request(
		CONNECT_URL,
		data=json.dumps({
			"action": action,
			"version": 6,
			"params": params,
		}).encode("utf-8"),
		headers={"Content-Type": "application/json"},
	)
	try:
		with urllib.request.urlopen(req) as resp:
			data = json.load(resp)
	except urllib.error.URLError as e:
		print(f"Error: could not connect to AnkiConnect at {CONNECT_URL}: {e}", file=sys.stderr)
	except json.JSONDecodeError as e:
		print(f"Error: received invalid JSON from AnkiConnect: {e}", file=sys.stderr)
	except Exception as e:
		print(f"Error: request to AnkiConnect failed: {e}", file=sys.stderr)

	if data.get("error") is not None:
		print(f"Error: AnkiConnect returned an error for action '{action}': {data['error']}", file=sys.stderr)

	return data["result"]

# Anki card data type
@dataclass
class AnkiCard:
	model_name: str
	tags: list[str] = field(default_factory=list)
	fields: list[tuple[str, str]] = field(default_factory=list)

	def is_empty(self) -> bool:
		return not self.fields

	def add_field(self, field_name: str, contents: str, top: bool = False) -> None:
		if not any(f == field_name for f, _ in self.fields):
			if top:
				self.fields.insert(0, (field_name, contents))
			else:
				self.fields.append((field_name, contents))

	def add_tag(self, tag: str) -> None:
		self.tags.append(tag)

	def to_note(self, deck_name: str) -> dict:
		return {
				"deckName": deck_name,
				"modelName": self.model_name,
				"fields": dict(self.fields),
				"tags": self.tags,
			}

	def add(self, deck_name: str) -> int:
		invoke("createDeck", deck=deck_name)
		return invoke("addNote", note=self.to_note(deck_name))
	
	# Print representation
	def __str__(self) -> str:
		if self.is_empty():
			return "None"

		width = terminal_box_width(max_width=90, min_width=50)
		inner = width - 4
		title = f"Card '{self.fields[0][1]}' ({CC.BOLD}{self.model_name}{CC.RESET})"
		lines: list[str] = []
		lines.append("┌" + "─" * (width - 2) + "┐")
		lines.append(box_row(title, inner))
		lines.append("├" + "─" * (width - 2) + "┤")

		for name, value in self.fields:
			lines.extend(format_field_rows(name, value, inner))

		if self.tags:
			lines.append("├" + "─" * (width - 2) + "┤")
			tags_content = "(None)" if not any(self.tags) else ", ".join(self.tags)
			lines.append(box_row(f"{CC.BOLD}Tags:{CC.RESET} {tags_content}", inner))

		lines.append("└" + "─" * (width - 2) + "┘")

		return "\n".join(lines)
	
	def __repr__(self) -> str:
		return str(self)

# Returns note IDs for exact key_name key_value match
def find_exact_notes(deck_name: str, key_name: str, key_value: str) -> list[int]:
	query = f'deck:"{deck_name}" {key_name}:"{key_value}"'
	note_ids = invoke("findNotes", query=query)

	matched = []
	for note in invoke("notesInfo", notes=note_ids) if note_ids else []:
		fields = note["fields"]
		if key_name in fields and fields[key_name]["value"] == key_value:
			matched.append(note["noteId"])
	return matched

# Adds tag to exact match. Returns 0 - success, 1 - error
def add_tag_match(deck_name: str, key_name: str, key_value: str, tag: str):
	matched = find_exact_notes(deck_name, key_name, key_value)
	if not matched: return 1

	result = invoke("addTags", notes=matched, tags=tag)

	if result is None: return 0
	else: return 1

# Attempts to unsuspend cards by exact match. Returns 0 : change made, 1 : error / no exact match, 2 : already suspended
def unsuspend_match(deck_name: str, key_name: str, key_value: str) -> int:
	card_ids = find_exact_notes(deck_name, key_name, key_value)

	if not card_ids: return 1

	statuses = invoke("areSuspended", cards=card_ids)
	suspended_cards = [
		card_id
		for card_id, is_suspended in zip(card_ids, statuses)
		if is_suspended
	]

	if not suspended_cards: return 2
	result = invoke("unsuspend", cards=suspended_cards)
	if result is True or result is None: return 0

	return 1