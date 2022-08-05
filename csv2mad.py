#!/bin/python3
# 20210425 Written by Felix Leger (aka @barfood#4348), with guidance from Porkchop Express.
# https://felixleger.com || https://misteraddons.com

"""
How to use:
    python3 csv2mad.py ARCADE_METADATA_FILE(.csv)

This will generate an "output_mads/" folder with 1 file per line in your ARCADE_METADATA_FILE.
"""

import os
import sys
import tqdm
import datetime
import numpy as np
import pandas as pd

if len(sys.argv) != 2:
    print("Please call the script as follows")
    print("python3 csv2mad.py ARCADE_METADATA_FILE(.csv)")
    sys.exit(1)

ARCADE_METADATA_CSV = sys.argv[1]
df = pd.read_csv(ARCADE_METADATA_CSV, na_values="", dtype=str)
df = df.replace(np.nan, '', regex=True)
MAD_NAME_COLUMN = "name"

# Create output directory
OUTPUT_DIR = "mad"
os.makedirs(OUTPUT_DIR, exist_ok=True)

############### MAIN LOOP #########################
for _, game in tqdm.tqdm(df.iterrows(), desc="Generating mads", total=df.shape[0]):

    # Alternate mads are created in subfolders
    # if len(game.alternative) > 0:
    #     alternate_folder = os.path.join(OUTPUT_DIR, "_alternatives", "_"+game.alternative.replace("&amp;", "&"))
    #     os.makedirs(alternate_folder, exist_ok=True)
    #     mad_filename = os.path.join(alternate_folder, game[MAD_NAME_COLUMN] + ".mad")
    # else:
    mad_filename = os.path.join(OUTPUT_DIR, game[MAD_NAME_COLUMN] + ".mad")

    with open(mad_filename.replace("&amp;", "&"), 'w') as f:  # Write in file as utf-8
        f.write("<?xml version=\"1.0\" ?>\n")
        f.write("<misterarcadedescription>\n\n")
        for key in game.keys():
            #if key == MAD_NAME_COLUMN:
                # We don't want to include the MAD name as a field in the MAD itself.
                #continue
            #elif "linebreak" in key:
            if "linebreak" in key:
                # Any column that contains "linebreak" in its column name will be skipped and replaced by a
                # new line in the MAD instead. (Remember, column names must be unique, so they will be
                # linebreak1, linebreak2, etc.)
                f.write("\n")
                continue

            # Indent
            f.write("\t")

            if len(game[key]) > 0 and game[key][0] == "<":
                # Special case, some fields contain xml code inside them (they are complete without us
                # handling writing the xml tag around the value)
                    f.write(game[key].replace("\\n", "\n\t\t") + "\n")
            else:
                if key in ["manufacturer", "series"]:
                    for i, val in enumerate(game[key].split(" / ")):
                        f.write("<{}>{}</{}>".format(key, val, key) + "\n")
                        if i < len(game[key].split(" / ")) - 1:
                            f.write("\t")
                else:
                    f.write("<{}>{}</{}>\n".format(key, game[key], key))

        f.write("</misterarcadedescription>")
############### END MAIN LOOP ##########################

print("MADs have been generated in folder {}/".format(OUTPUT_DIR))
