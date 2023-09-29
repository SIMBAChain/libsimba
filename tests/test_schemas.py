import os
import unittest
from libsimba import SearchFilter, FilterOp, FieldFilter, FileDict, File
from libsimba.utils import build_url
from urllib.parse import unquote
import pytest


class SchemaTestCase(unittest.TestCase):
    @pytest.mark.unit
    def test_filters(self):
        filter = SearchFilter(
            filters=[
                FieldFilter(field="foo", op=FilterOp.EQ, value="bar"),
                FieldFilter(field="foo.choo.boo", op=FilterOp.EXACT, value="bar"),
                FieldFilter(field="foo", op=FilterOp.IEXACT, value="BAR"),
                FieldFilter(field="fiz", op=FilterOp.CONTAINS, value="boo"),
                FieldFilter(field="foz", op=FilterOp.GT, value=2),
                FieldFilter(field="biz", op=FilterOp.IN, value=[2, 3, 4]),
            ],
            fields=["foo", "fiz"],
            limit=2,
            offset=2,
        )
        has_filter = filter.has_filter(field="foo.choo.boo")
        self.assertTrue(has_filter)

        url = unquote(
            build_url("http://localhost", "path/to/stuff", filter.filter_query)
        )
        self.assertEqual(
            "http://localhost/path/to/stuff?filter[foo]=bar&filter[foo.choo.boo]=bar&filter[foo.iexact]=BAR&filter[fiz.contains]=boo&filter[foz.gt]=2&filter[biz.in]=2,3,4&fields=foo,fiz&limit=2&offset=2",
            url,
        )

    @pytest.mark.unit
    def test_files(self):
        data_dir = os.path.join(os.path.dirname(__file__), "data")
        f1 = File(path=os.path.join(data_dir, "file1.txt"), mime="text/plain")
        print("\n\n\nf1111: ", f1)
        self.assertEqual("file1.txt", f1.name)
        pointer = f1.open()
        # opened in binary mode so matches on bytes
        self.assertEqual(b"Hello world", pointer.read())
        f1.close()
        f1.close()
        f2 = File(path=os.path.join(data_dir, "file2.txt"))
        self.assertEqual("file2.txt", f2.name)
        self.assertEqual("text/plain", f2.mime)
        dict1 = FileDict(file=f1)
        self.assertEqual(1, len(dict1.files))
        dict2 = FileDict(files=[f1, f2])
        self.assertEqual(2, len(dict2.files))
        f3 = File(name="f1.txt", fp=open(os.path.join(data_dir, "file1.txt")))
        self.assertEqual("f1.txt", f3.name)
        self.assertEqual("text/plain", f3.mime)
        pointer = f3.open()
        # opened in text mode (to be avoided) so matches on string
        self.assertEqual("Hello world", pointer.read())
        f3.close()

        pointer = open(os.path.join(data_dir, "file1.txt"))
        try:
            f4 = File(fp=pointer)
            self.assertFalse(True)
        except:
            pass
        pointer.close()

        pointer = open(os.path.join(data_dir, "file1.txt"))
        try:
            f5 = File(path=os.path.join(data_dir, "file1.txt"), fp=pointer)
        except:
            self.assertFalse(True)
        pointer.close()


if __name__ == "__main__":
    unittest.main()
