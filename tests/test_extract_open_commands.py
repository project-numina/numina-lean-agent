import unittest
from scripts.extract_sublemmas import create_statement_with_lemmas


class OpenCommandsTests(unittest.TestCase):
    def test_preserves_scoped_and_selective_opens(self):
        original = "open scoped BigOperators\nopen Nat (succ add_comm)\ntheorem main : True := by\n  trivial"
        lemma = "open scoped BigOperators\nopen Nat hiding succ\nlemma helper : True := by\n  trivial"
        code, _ = create_statement_with_lemmas(original, [lemma])
        opens = [line for line in code.splitlines() if line.startswith("open ")]
        self.assertEqual(opens, ["open Nat (succ add_comm)", "open Nat hiding succ",
                                 "open scoped BigOperators"])
        self.assertIn("theorem main", code)
        self.assertIn("lemma helper", code)

    def test_preserves_renaming(self):
        code, _ = create_statement_with_lemmas(
            "open Nat renaming succ -> next\ntheorem main : True := by\n  trivial", [])
        self.assertIn("open Nat renaming succ -> next\n", code)
