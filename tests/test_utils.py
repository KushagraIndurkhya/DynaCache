import unittest
from dynacache.src.utils import serialize_to_ascii, deserialize_from_ascii

class TestUtils(unittest.TestCase):

    def test_serialization(self):
        data = {'a': 1, 'b': 'hello'}
        serialized = serialize_to_ascii(data)
        deserialized = deserialize_from_ascii(serialized)
        self.assertEqual(data, deserialized)

if __name__ == '__main__':
    unittest.main()
