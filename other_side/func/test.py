import sys, os
sys.path.append(os.path.dirname(__file__))

from patch_file import patch_file

# مجلد العمل
WORKDIR = os.path.abspath(".")

# ملف الاختبار
TARGET_FILE = "test_patch_target.py"

# محتوى الملف قبل التعديل
INITIAL_CONTENT = """\
def calculate(x, y):
    return x + y
"""

# إنشاء ملف الاختبار
with open(TARGET_FILE, "w", encoding="utf-8") as f:
    f.write(INITIAL_CONTENT)

# content_before (يجب أن يطابق 100%)
content_before = """\
def calculate(x, y):
    return x + y
"""

# content_after
content_after = """\
function
    if y == 0:
        raise ValueError("y cannot be zero")
    return x + y
    
"""

# استدعاء الأداة
result = patch_file(
    working_directory=WORKDIR,
    file_path=TARGET_FILE,
    content_before=content_before,
    content_after=content_after
)

print(result)
