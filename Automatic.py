import os
import shutil
import subprocess
import time

# get current date in yymmdd format
current_date = time.strftime("%y%m%d")

# delete the folder called mad in current directory
if os.path.exists("mad"):
  shutil.rmtree("mad")

# rename MiSTerArcadeDatabase - sheet1.csv to ArcadeDatabase230109.csv if ArcadeDatabase230109.csv does not exist and MiSTerArcadeDatabase - sheet1.csv exists
if not os.path.exists("ArcadeDatabase" + current_date + ".csv") and os.path.exists("MiSTerArcadeDatabase - sheet1.csv"):
  os.rename("MiSTerArcadeDatabase - sheet1.csv", "ArcadeDatabase" + current_date + ".csv")

# execute the csv2mad.py script
subprocess.call(["python", "csv2mad.py", "ArcadeDatabase" + current_date + ".csv"])
