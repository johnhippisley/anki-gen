from pathlib import Path
import argparse
import json
import csv
from utils import db
from utils import anki

comma_split = lambda s: [] if s is None else [item.strip() for item in s.split(",")]

BOLD = "\033[1m"
RESET = "\033[0m"

def parse_args():
	source_file = Path(__file__).name
	parser = argparse.ArgumentParser(prog=source_file, description ="Automated generation for Anki vocabularly cards.")
	parser.add_argument("-p", "--path", required=True, help="Text file of seeds (or .csv) to import")
	parser.add_argument("-m", "--card-type", required=True, help="Name of the Anki card type")
	parser.add_argument("-r", "--preview", action="store_true", help="Preview mode.")
	parser.add_argument("-d", "--deck-name", help="Name of the Anki deck")
	parser.add_argument("-t", "--tag", default=None, help="Tag name to apply to imported cards")
	parser.add_argument("-c", "--config", default="config.json", help='Database configuration JSON. Default: "config.json"')
	parser.add_argument(
		"-v", "--verbose", nargs="?", const=1, default=0, type=int, choices=[0, 1, 2],
		help="Verbosity level: 0 by default, 1 with --verbose, 2 with --verbose=2"
	)	
	return parser.parse_args()

# Global configuration
config: db.Configuration | None = None

# Returns -1 : card is already unsuspended, 0 : created new card, 1 : error, 2 : unsuspended card 
def make_card(deck_name: str, model_name: str, seed: str, tags: list[str], verbose: int):
	unsuspend_ret = anki.unsuspend_match(deck_name, config.anki_seed_field, seed)
	if unsuspend_ret == 0:
		print(f"Unsuspended card '{seed}'")
		return 2
	elif unsuspend_ret == 2:
		print(f"Card '{seed}' exists and is already unsuspended.\n")
		return -1
	else:
		print(f"Card '{seed}' does not exist. Generating...")
		card = db.gen_anki_card(config, seed, model_name, tags, verbose)
		if card is None:
			print(f"No data for card '{seed}.'")
			return 1
		card.add(deck_name)
		if verbose:
			print(card)
			print()
		return 0

def txt_mode(args, config):
	with open(args.path, "r", encoding="utf-8") as f:
		n_unsuspended = 0
		n_created = 0
		omitted = []
		for i, line in enumerate(f):
			print(f"{BOLD}[{i + 1}]{RESET}", end = " ")
			seed = line.rstrip("\n")
			if args.preview:
				card = db.gen_anki_card(config, seed, args.card_type, comma_split(args.tag), args.verbose)
				if card is not None:
					print()
					print(card)
				else:
					print(f"No data for card '{seed}'.")
					omitted = omitted + [seed]
			else:
				ret = make_card(args.deck_name, args.card_type, seed, comma_split(args.tag), args.verbose)
				if ret == 0:
					n_created = n_created + 1
				elif ret == 2:
					n_unsuspended = n_unsuspended + 1
		
		if not args.preview:
			print(f"Unsuspended {n_unsuspended} card(s), created {n_created} card(s) in deck '{args.deck_name}'")
		print("No data for: ", end = "")
		print(", ".join(omitted) if omitted else "None")

def csv_mode(args, config):
	with open(args.path, "r", encoding="utf-8", newline="") as f:
		n_unsuspended = 0
		n_created = 0
		omitted = []
		reader = csv.reader(f)
		next(reader, None)  # skip header row
		for i, row in enumerate(reader):
			print(f"{BOLD}[{i + 1}]{RESET}", end=" ")
			tag, seed = row[0], row[1]
			if args.preview:
				card = db.gen_anki_card(config, seed, args.card_type, comma_split(args.tag) + [tag], args.verbose)
				if card is not None:
					print()
					print(card)
				else:
					print(f"No data for card '{seed}'.")
					omitted = omitted + [seed]
			else:
				ret = make_card(args.deck_name, args.card_type, seed, comma_split(args.tag) + [tag], args.verbose)
				if ret == 0:
					n_created = n_created + 1
				elif ret == 2:
					n_unsuspended = n_unsuspended + 1
		
		if not args.preview:
			print(f"Unsuspended {n_unsuspended} card(s), created {n_created} card(s) in deck '{args.deck_name}'")
		print("No data for: ", end = "")
		print(", ".join(omitted) if omitted else "None")


if __name__ == "__main__":
	args = parse_args()
	config = db.get_configuration(args.config)

	if isinstance(config, db.Configuration):
		print(f"Successfully loaded configuration {args.config}")
	else:
		print(f"Error loading configuration {args.config}")
		exit(1)
	if args.preview:
		print("[Previewing cards]", end=" ")
	elif args.deck_name is None:
		print("Deck name not provided.")
		exit(1)

	ext = Path(args.path).suffix

	if ext == ".txt":
		print("Launching in .txt seed mode.\n")
		txt_mode(args, config)
	elif ext == ".csv":
		print("Launching in .csv seed mode.\n")
		csv_mode(args, config)
		