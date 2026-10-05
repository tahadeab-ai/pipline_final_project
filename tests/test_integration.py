"""Unit tests for DataIntegrator (Test 7: Multi-Source Integration)."""
import unittest
import pandas as pd

from app.transformation.integration import DataIntegrator


class TestDataIntegrator(unittest.TestCase):
    def setUp(self):
        self.integrator = DataIntegrator(join_key="student_id")

    def test_multi_source_integration(self):
        """Test 7: Verify successful relational joining and data lineage assignment."""
        csv_df = pd.DataFrame([
            {"student_id": 1001, "student_name": "Ahmed Ali", "city": "Sanaa"}
        ])
        api_df = pd.DataFrame([
            {"student_id": 1001, "gpa": 3.75, "attendance": 92.0}
        ])
        db_df = pd.DataFrame([
            {"student_id": 1001, "course": "Python", "score": 95.0}
        ])

        integrated = self.integrator.integrate(csv_df, api_df, db_df)

        self.assertEqual(len(integrated), 1)
        row = integrated.iloc[0]
        self.assertEqual(row["student_id"], 1001)
        self.assertEqual(row["student_name"], "Ahmed Ali")
        self.assertEqual(row["gpa"], 3.75)
        self.assertEqual(row["attendance"], 92.0)
        self.assertEqual(row["course"], "Python")
        self.assertEqual(row["score"], 95.0)
        self.assertEqual(row["data_lineage"], "CSV + API + DATABASE")


if __name__ == "__main__":
    unittest.main()
