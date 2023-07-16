#!/bin/python3

import os
import sys
import csv
import tqdm

if len(sys.argv) != 2:
    print("Please call the script as follows")
    print("python3 csv2mad.py ARCADE_METADATA_FILE(.csv)")
    sys.exit(1)

ARCADE_METADATA_CSV = sys.argv[1]
MAD_NAME_COLUMN = "name"
OUTPUT_DIR = "mad"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# MAIN LOOP
with open(ARCADE_METADATA_CSV, "r") as file:
    csv_reader = csv.DictReader(file)
    total_rows = sum(1 for _ in csv_reader)
    file.seek(0)  # Reset file pointer for tqdm
    next(csv_reader)  # Skip header row

    for game in tqdm.tqdm(csv_reader, desc="Generating mads", total=total_rows):
        mad_filename = os.path.join(OUTPUT_DIR, game[MAD_NAME_COLUMN] + ".mad")

        with open(mad_filename.replace("&amp;", "&"), 'w') as f:
            f.write("<?xml version=\"1.0\" ?>\n")
            f.write("<misterarcadedescription>\n\n")

            for key, value in game.items():
                if "linebreak" in key:
                    f.write("\n")
                    continue

                f.write("\t")

                if len(value) > 0 and value[0] == "<":
                    f.write(value.replace("\\n", "\n\t\t") + "\n")
                else:
                    if key in ["manufacturer", "series"]:
                        values = value.split(" / ")
                        for i, val in enumerate(values):
                            f.write(f"<{key}>{val}</{key}>\n")
                            if i < len(values) - 1:
                                f.write("\t")
                    else:
                        f.write(f"<{key}>{value}</{key}>\n")

            f.write("</misterarcadedescription>")

print(f"MADs have been generated in folder {OUTPUT_DIR}/")