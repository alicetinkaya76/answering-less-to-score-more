import unittest

from fg.parse import loose_parse, parse_both, strict_parse


class TestStrict(unittest.TestCase):
    def test_plain(self):
        self.assertEqual(strict_parse("EVET"), "EVET")
        self.assertEqual(strict_parse("hayır"), "HAYIR")
        self.assertEqual(strict_parse("Hayir."), "HAYIR")
        self.assertEqual(strict_parse("  EVET  \n"), "EVET")

    def test_prefixed(self):
        self.assertEqual(strict_parse("Cevap: EVET"), "EVET")
        self.assertEqual(strict_parse("Etiket: hayır"), "HAYIR")

    def test_turkish_casing(self):
        # Türkçe I/İ tuzağı: casefold değil tr_fold kullanılmalı
        self.assertEqual(strict_parse("HAYIR"), "HAYIR")
        # 'HAYİR' yaygın LLM yazım hatasıdır; belirsizlik yaratmadığı için kabul edilir
        self.assertEqual(strict_parse("HAYİR"), "HAYIR")

    def test_first_line_only(self):
        self.assertIsNone(strict_parse("Bu tweet zor bir örnek.\nEVET"))

    def test_both_labels_abstain(self):
        self.assertIsNone(strict_parse("EVET ya da HAYIR olabilir"))

    def test_garbage_and_empty(self):
        self.assertIsNone(strict_parse(""))
        self.assertIsNone(strict_parse(None))
        self.assertIsNone(strict_parse("Bu konuda yorum yapamam."))
        self.assertIsNone(strict_parse("offensive"))

    def test_no_substring_false_positive(self):
        self.assertIsNone(strict_parse("hayırlı işler"))  # 'hayırlı' ≠ 'hayır'


class TestLoose(unittest.TestCase):
    def test_recovers_buried_answer(self):
        self.assertEqual(loose_parse("Bu tweet açıkça saldırgan.\n\nCevap: EVET"), "EVET")
        self.assertEqual(loose_parse('{"karar": "hayır", "gerekce": "..."} '), "HAYIR")

    def test_first_occurrence_wins(self):
        self.assertEqual(loose_parse("EVET... ama belki HAYIR"), "EVET")

    def test_none_when_absent(self):
        self.assertIsNone(loose_parse("kararsızım"))

    def test_superset_property(self):
        s, l = parse_both("EVET")
        self.assertEqual((s, l), ("EVET", "EVET"))
        s, l = parse_both("Açıklama uzun.\nHAYIR")
        self.assertEqual((s, l), (None, "HAYIR"))


if __name__ == "__main__":
    unittest.main()
