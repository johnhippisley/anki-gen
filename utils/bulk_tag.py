import csv
import anki

def anki_bulk_tag(tag: str, collection: list):
	# ...

# Expects format KEY_NAME, VALUE, TAG
def anki_bulk_tag_csv(deck_name: str, path: str, delim = ","):
	try:
		with open(path, "r", encoding="utf-8-sig", newline="") as f:
			reader = csv.DictReader(f, delimiter=delim)
			key_name = reader.fieldnames[0]
			for row in reader:
				key_value = row[reader.fieldnames[1]]
				tag = row[reader.fieldnames[2]]
				anki_add_tag(deck_name, key_name, key_value, tag)
	except FileNotFoundError:
		print(f"Error: {file} not found")
	except PermissionError:
		print("Error: permission denied")
	except OSError as e:
		print(f"Error opening file: {e}")

