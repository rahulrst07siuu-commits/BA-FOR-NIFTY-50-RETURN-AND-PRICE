import unittest
from pathlib import Path
import pandas as pd
import py_compile

ROOT = Path(__file__).resolve().parent

class ProjectSmokeTests(unittest.TestCase):
    def test_app_compiles(self):
        py_compile.compile(str(ROOT / "app.py"), doraise=True)

    def test_embedded_workbook_exists(self):
        self.assertTrue((ROOT / "market_data.xlsx").exists())

    def test_eight_sheets_present(self):
        self.assertEqual(len(pd.ExcelFile(ROOT / "market_data.xlsx").sheet_names), 8)

    def test_daily_monthly_separate_and_expected_sizes(self):
        daily = pd.read_excel(ROOT / "market_data.xlsx", sheet_name="Daily Nifty Model Data", header=3)
        monthly = pd.read_excel(ROOT / "market_data.xlsx", sheet_name="Monthly SIP FII DII", header=3)
        self.assertEqual(len(daily), 22)
        self.assertEqual(len(monthly), 130)
        self.assertIn("Target_Next_Session_Return_Pct", daily.columns)
        self.assertIn("SIP Inflow (cr)", monthly.columns)
        self.assertNotIn("SIP Inflow (cr)", daily.columns)

    def test_missing_sip_not_zero_filled(self):
        monthly = pd.read_excel(ROOT / "market_data.xlsx", sheet_name="Monthly SIP FII DII", header=3)
        self.assertEqual(int(monthly["SIP Inflow (cr)"].isna().sum()), 5)

if __name__ == "__main__":
    unittest.main()
