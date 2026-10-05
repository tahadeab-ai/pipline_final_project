"""End-to-end integration tests (Test 8: Final Dataset Creation)."""
import unittest
from pathlib import Path

from main import PipelineOrchestrator


class TestPipelineE2E(unittest.TestCase):
    def test_end_to_end_pipeline_execution(self):
        """Test 8: Verify pipeline runs end-to-end and produces final_dataset.csv and rejected_records.csv."""
        orchestrator = PipelineOrchestrator()
        metrics = orchestrator.run(force_recompute=True)

        self.assertIn("valid_records", metrics)
        self.assertGreater(metrics["valid_records"], 0)

        final_csv = Path(orchestrator.config["paths"]["processed_output"])
        rejected_csv = Path(orchestrator.config["paths"]["rejected_output"])
        log_file = Path(orchestrator.config["paths"]["log_file"])

        self.assertTrue(final_csv.exists(), "final_dataset.csv was not created")
        self.assertTrue(rejected_csv.exists(), "rejected_records.csv was not created")
        self.assertTrue(log_file.exists(), "pipeline.log was not created")

        # Verify final_dataset.csv is non-empty and contains derived columns
        import pandas as pd
        df_final = pd.read_csv(final_csv)
        self.assertFalse(df_final.empty)
        self.assertIn("performance_level", df_final.columns)
        self.assertIn("attendance_status", df_final.columns)
        self.assertIn("data_lineage", df_final.columns)


if __name__ == "__main__":
    unittest.main()
