import sys
import os
sys.path.append(os.getcwd())
from test.patch_file import patch_file

test_file = "test_final.py"
with open(test_file, "w") as f:
    f.write("line1\nline2\nline3\n")

print(patch_file(".", test_file, "line2", "line_two_updated\nline_new"))

if os.path.exists(test_file):
    os.remove(test_file)
