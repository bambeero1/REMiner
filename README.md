# REsaMiner

This Python script is a web crawler designed to extract and process real estate information. The script utilizes the Playwright library for web scraping, Aiosqlite for SQLite database interactions, and Rich for console logging.

## Dependencies

Make sure to install the required dependencies using the following command:
```bash
pip install playwright aiosqlite playwright_stealth argparse rich
```

## Usage

### Command-line Arguments

- `--sqlite`: Flag to save data to an SQLite database.
- `--json`: Flag to save data to a JSON file.
- `--st`: Starting page number for crawling.

### Example Usage

To start crawling from page 1 and save data to SQLite, run the following command:

```bash
python aqar.py --sqlite
```

To start crawling from a specific page (e.g., page 5) and save data to a JSON file, run:

```bash
python aqar.py --json --st 5
```

## Logging

The script uses the Rich library for logging, providing a visually appealing and informative console output.

## Database Schema

The SQLite database schema includes the following fields in the "Aqarat" table:

- `adid`: Ad ID (Primary Key)
- `title`: Ad title
- `description`: Ad description
- `author_name`: Author's name
- `price`: Ad price
- `filters`: Filters applied to the property
- `generic_values`: Values corresponding to the filters
- `cat`: Property category
- `author_url`: URL of the author's profile
- `city`: City of the property
- `citydir`: City district or part
- `dist`: District of the property
- `imgs`: URLs of images associated with the ad
- `map_url`: URL of the property on the map

## Rights

Mohammed Alraddadi
  - LinkedIn: [https://www.linkedin.com/in/raddadi/](https://www.linkedin.com/in/raddadi/)
  - Email: [r@ddadi.me](mailto:r@ddadi.me)

