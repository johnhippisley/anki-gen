# anki-gen

A configurable tool for generating Anki vocabulary cards.

<img src="media/demo.png" alt="Demo" width="700">

## Usage

```bash
python3 main.py [-h] -p PATH -m CARD_TYPE [-r] [-d DECK_NAME] [-t TAG] [-c CONFIG] [-v [{0,1,2}]]
```

### Arguments

| Option | Description |
|---|---|
| `-h`, `--help` | Show help message and exit |
| `-p PATH`, `--path PATH` | Path to the 'seed' file (.csv or .txt) |
| `-m CARD_TYPE`, `--model CARD_TYPE` | Anki card/model type to use |
| `-r`, `--preview` | Preview mode (doesn't add cards) |
| `-d DECK_NAME`, `--deck DECK_NAME` | Target Anki deck name |
| `-t TAG(S)`, `--tag TAG(S)` | Tag(s) to apply to imported cards |
| `-c CONFIG`, `--config CONFIG` | Path to .json configuration file |
| `-v [{0,1,2}]`, `--verbose [{0,1,2}]` | Verbosity level |

## Example Usage:
The following gives the output pictured above:

```bash
python3 main.py -d New -p my_vocabulary_list.txt -m 词汇 -t example-tag -v
```

`my_vocabulary_list.txt`:

```text
惊讶
缓解
...
```
## Dependencies

Requires Python 3 and the following dependencies:
- `pypinyin`
- `sqlite3`
- `wcwidth`

You'll also need to have the [AnkiConnect](https://ankiweb.net/shared/info/2055492159) plug-in installed.

Anki must be open while the script is running.

## JSON Config Format

The config file defines how input columns map onto Anki note fields and how cards should be created.

Example `config.json`:

```json
{
  "config": {
    "anki_seed_field": "Hanzi"
  },

  "data/cedict.db": {
    "name": "cedict",
    "condition": "simplified='{{seed}}'",
    "pinyin_fields": [
      "pinyin"
    ],
    "fields": {
      "simplified": ["Key", "Hanzi"],
      "pinyin": "Pinyin",
      "english": "English"
    }
  },

  "data/chin_example_sen.db": {
    "name": "examples",
	"condition": "simplified LIKE '%{{seed}}%'",
    "fields": {
      "simplified": "Usage",
      "pinyin": "SentencePinyin.1",
      "english": "SentenceMeaning"
    }
  }
}
```

Here the database column `simplified` will be copied into the Anki fields `Key` and `Hanzi`, etc.

## Input File Format

When using with a CSV file, it should be in the following format:

Example:

```csv
seed,tag
美丽,lesson-1
大楼,lesson-1
小笼包,lesson-2
```
