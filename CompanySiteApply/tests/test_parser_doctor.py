# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [TEST]
# Timestamp: 2026-09-15 23:05:00 +05:30
# Issue / Context: Automated unit tests for Parser Doctor (LineWrapHealer & EducationHealer).
# Changes Made: Created test suite verifying line-wrap healing, bullet preservation, and education inversion.
# Rationale: Ensures regression-free ATS resume healing per user specifications.
# Preventative Notes: Uses synthetic dummy test data; zero candidate PII.
# ==============================================================================

import unittest
from CompanySiteApply.parser_doctor.line_wrap_healer import LineWrapHealer
from CompanySiteApply.parser_doctor.education_healer import EducationHealer


class TestParserDoctor(unittest.TestCase):

    def test_line_wrap_healer_hyphenated_compound_word(self):
        corrupted = (
            "Architected and deployed cloud-\n"
            "native microservices using Docker and Kubernetes."
        )
        expected = (
            "Architected and deployed cloud-native microservices using Docker and Kubernetes."
        )
        healed = LineWrapHealer.heal_text(corrupted)
        self.assertEqual(healed, expected)

    def test_line_wrap_healer_hyphenated_syllable_split(self):
        corrupted = (
            "Led full-lifecycle software devel-\n"
            "opment and release management."
        )
        expected = (
            "Led full-lifecycle software development and release management."
        )
        healed = LineWrapHealer.heal_text(corrupted)
        self.assertEqual(healed, expected)

    def test_line_wrap_healer_soft_wrap(self):
        corrupted = (
            "Led a high-velocity engineering team responsible for developing\n"
            "scalable real-time payment processing pipelines."
        )
        expected = (
            "Led a high-velocity engineering team responsible for developing scalable real-time payment processing pipelines."
        )
        healed = LineWrapHealer.heal_text(corrupted)
        self.assertEqual(healed, expected)

    def test_line_wrap_healer_preserves_bullets(self):
        text_with_bullets = (
            "• Implemented end-to-end telemetry and observability with Prometheus.\n"
            "• Reduced database query latency by 45% through Redis caching.\n"
            "• Spearheaded CI/CD automation pipelines across 12 services."
        )
        healed = LineWrapHealer.heal_text(text_with_bullets)
        self.assertEqual(healed, text_with_bullets)

    def test_line_wrap_healer_multiline_bullet_wrapped(self):
        corrupted = (
            "• Architected scalable event-driven distributed system using Apache Kafka and\n"
            "Flink for high-throughput stream processing.\n"
            "• Designed database schemas and automated deployment pipelines."
        )
        expected = (
            "• Architected scalable event-driven distributed system using Apache Kafka and Flink for high-throughput stream processing.\n"
            "• Designed database schemas and automated deployment pipelines."
        )
        healed = LineWrapHealer.heal_text(corrupted)
        self.assertEqual(healed, expected)

    def test_education_healer_inversion(self):
        parsed_school = "Bachelor of Technology"
        parsed_degree = "National Institute of Technology"
        diagnosis = EducationHealer.diagnose_and_heal_entry(parsed_school, parsed_degree)
        
        self.assertTrue(diagnosis["was_modified"])
        self.assertEqual(diagnosis["school"], "National Institute of Technology")
        self.assertEqual(diagnosis["degree"], "Bachelor of Technology")

    def test_education_healer_ground_truth_alignment(self):
        parsed_school = "NIT"
        parsed_degree = "BTech"
        gt = [{
            "institution": "National Institute of Technology, Kurukshetra",
            "degree": "Bachelor of Technology in Computer Science",
            "field_of_study": "Computer Science & Engineering"
        }]
        diagnosis = EducationHealer.diagnose_and_heal_entry(parsed_school, parsed_degree, ground_truth_education=gt)
        self.assertTrue(diagnosis["was_modified"])
        self.assertEqual(diagnosis["field_of_study"], "Computer Science & Engineering")


if __name__ == "__main__":
    unittest.main()
