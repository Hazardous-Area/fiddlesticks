import io
from pathlib import Path

import msoffcrypto

# import pandas as pd

file = Path(__file__).parent / "tests" / "test.xlsx"
encrypted = io.BytesIO(file.read_bytes())
stream = io.BytesIO()

office_file = msoffcrypto.OfficeFile(encrypted)

for pw in ["test3", "test"]:
    office_file.load_key(password=pw)
    try:
        office_file.decrypt(stream)
        break
    except msoffcrypto.exceptions.InvalidKeyError:
        pass


# df = pd.read_excel(stream)
# print(df)
