from __future__ import annotations

import unittest

from data_engine import load_data, maybe_handle_structured_question
from sample_comparison import compare_samples, find_similar_samples


class SampleComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = load_data()

    def test_similar_sample_is_found(self) -> None:
        results = find_similar_samples(self.data, "4301828993017651", top_k=3)

        self.assertTrue(results)
        self.assertNotEqual(results[0]["local_id"], "4301828993017651")
        self.assertIn("fit", results[0])
        self.assertGreaterEqual(results[0]["bom_similarity"], 0)

    def test_same_material_has_no_bom_delta(self) -> None:
        comparison = compare_samples(self.data, "4301828993017651", "4301800000000012")

        self.assertEqual(comparison["bom"]["similarity"], 1.0)
        self.assertEqual(comparison["bom"]["only_base"], [])
        self.assertEqual(comparison["bom"]["only_candidate"], [])

    def test_bom_differences_are_reported(self) -> None:
        comparison = compare_samples(self.data, "4301828993017651", "0805038020400411")

        self.assertLess(comparison["bom"]["similarity"], 1.0)
        self.assertTrue(comparison["bom"]["only_base"] or comparison["bom"]["only_candidate"])

    def test_missing_bom_data_is_explicit(self) -> None:
        data = {
            "samples": [
                {"local_id": "A", "global_id": "G-A", "material_nr": "MAT-A", "status": "available"},
                {"local_id": "B", "global_id": "G-B", "material_nr": "MAT-B", "status": "available"},
            ],
            "availability": [],
            "bom": [],
            "test_runs": [],
            "defects": [],
        }

        comparison = compare_samples(data, "A", "B")
        message = " ".join(comparison["bom"]["missing_information"])

        self.assertIn("BOM", message)
        self.assertEqual(comparison["bom"]["similarity"], 0.0)

    def test_chat_routes_difference_question(self) -> None:
        handled = maybe_handle_structured_question(
            "Was ist anders bei 4301828993017651 und 0805038020400411?",
            self.data,
        )

        self.assertIsNotNone(handled)
        self.assertIn("Einschätzung", handled["answer"])
        self.assertIn("Tests nur im", handled["answer"])


if __name__ == "__main__":
    unittest.main()
