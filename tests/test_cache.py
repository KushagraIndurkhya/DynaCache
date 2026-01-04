import unittest
from unittest.mock import patch, MagicMock, Mock
import time
from dynacache.src import DynamoDBCache
from dynacache.src.utils import serialize_to_ascii

class TestDynamoDBCache(unittest.TestCase):

    @patch('dynacache.src.cache.boto3')
    def setUp(self, mock_boto3):
        self.mock_dynamodb = MagicMock()
        mock_boto3.client.return_value = self.mock_dynamodb
        # Prevent create_table from being called in every test
        self.mock_dynamodb.create_table.side_effect = self.mock_dynamodb.exceptions.ResourceInUseException
        self.cache = DynamoDBCache(cache_table_name='test_table', aws_region='us-east-1')

    def test_cache_miss(self):
        """Test the scenario where the item is not in the cache."""
        mock_func = Mock(return_value=3)
        mock_func.__name__ = 'mock_func'

        @self.cache.cache_response(ttl_seconds=3600)
        def my_function(x, y):
            return mock_func(x, y)

        # Simulate cache miss
        self.mock_dynamodb.get_item.return_value = {}

        result = my_function(1, 2)

        self.assertEqual(result, 3)
        mock_func.assert_called_once_with(1, 2)
        self.mock_dynamodb.get_item.assert_called_once()
        self.mock_dynamodb.put_item.assert_called_once()

    def test_cache_hit(self):
        """Test the scenario where the item is in the cache and not expired."""
        mock_func = Mock(return_value=5)
        mock_func.__name__ = 'mock_func'

        @self.cache.cache_response(ttl_seconds=3600)
        def my_function(x, y):
            return mock_func(x, y)

        args = (3, 2)
        key = serialize_to_ascii((args, {}))
        cached_result = serialize_to_ascii(5)
        future_ttl = str(int(time.time() + 3600))

        # Simulate cache hit
        self.mock_dynamodb.get_item.return_value = {
            "Item": {
                "cache_key": {"S": key},
                "cached_data": {"S": cached_result},
                "ttl": {"N": future_ttl}
            }
        }

        result = my_function(3, 2)

        self.assertEqual(result, 5)
        mock_func.assert_not_called() # The original function should not be called
        self.mock_dynamodb.get_item.assert_called_once()
        self.mock_dynamodb.put_item.assert_not_called() # put_item should not be called on a cache hit

    def test_cache_expired(self):
        """Test the scenario where the item is in the cache but has expired."""
        mock_func = Mock(return_value=10)
        mock_func.__name__ = 'mock_func'

        @self.cache.cache_response(ttl_seconds=3600)
        def my_function(x, y):
            return mock_func(x, y)

        args = (4, 6)
        key = serialize_to_ascii((args, {}))
        cached_result = serialize_to_ascii(9) # Old result
        past_ttl = str(int(time.time() - 10)) # TTL is 10 seconds in the past

        # Simulate expired cache item
        self.mock_dynamodb.get_item.return_value = {
            "Item": {
                "cache_key": {"S": key},
                "cached_data": {"S": cached_result},
                "ttl": {"N": past_ttl}
            }
        }

        result = my_function(4, 6)

        self.assertEqual(result, 10) # Should return the new result
        mock_func.assert_called_once_with(4, 6) # The original function should be called
        self.mock_dynamodb.get_item.assert_called_once()
        self.mock_dynamodb.put_item.assert_called_once() # The cache should be updated

if __name__ == '__main__':
    unittest.main()
