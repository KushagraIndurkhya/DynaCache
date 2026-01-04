import boto3
import logging
import time
from botocore.exceptions import BotoCoreError, ClientError
from functools import wraps
from .config import load_config
from .utils import serialize_to_ascii, deserialize_from_ascii
from .exceptions import CacheException

logger = logging.getLogger(__name__)

class DynamoDBCache:
    def __init__(self, cache_table_name, defaultTTL=3600, aws_region=None, config_file=None, aws_access_key_id=None, aws_secret_access_key=None, aws_session_token=None):
        self.config = {}
        if config_file:
            self.config = load_config(config_file)
        self.aws_access_key_id = aws_access_key_id or self.config.get(
            "aws_access_key_id")
        self.aws_secret_access_key = aws_secret_access_key or self.config.get(
            "aws_secret_access_key")
        self.aws_session_token = aws_session_token or self.config.get(
            "aws_session_token")
        self.aws_region = aws_region or self.config["aws_region"]
        self.cache_table_name = cache_table_name
        self.dynamodb = self.setup_dynamodb()
        try:
            self.create_cache_table()
        except Exception as e:
            raise CacheException("Failed to create cache table")
        self.defaultTTL = defaultTTL

    def setup_dynamodb(self):
        if not self.aws_access_key_id or not self.aws_secret_access_key:
            return boto3.client("dynamodb", region_name=self.aws_region)
        else:
            return boto3.client(
                "dynamodb",
                region_name=self.aws_region,
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                aws_session_token=self.aws_session_token
            )

    def create_cache_table(self):
        try:
            self.dynamodb.create_table(
                TableName=self.cache_table_name,
                KeySchema=[
                    {
                        "AttributeName": "cache_key",
                        "KeyType": "HASH"
                    }
                ],
                AttributeDefinitions=[
                    {
                        "AttributeName": "cache_key",
                        "AttributeType": "S"
                    }
                ],
                ProvisionedThroughput={
                    "ReadCapacityUnits": 5,
                    "WriteCapacityUnits": 5
                }
            )
            self.dynamodb.get_waiter('table_exists').wait(
                TableName=self.cache_table_name)
            self.dynamodb.update_time_to_live(
                TableName=self.cache_table_name,
                TimeToLiveSpecification={
                    'Enabled': True,
                    'AttributeName': 'ttl'
                })
        except self.dynamodb.exceptions.ResourceInUseException:
            pass  # Table already exists

    def handle_aws_exceptions(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except (BotoCoreError, ClientError) as e:
                logger.error(f"AWS Error: {str(e)}")
                raise CacheException(f"AWS Error: {str(e)}")
        return wrapper

    def cache_response(self, ttl_seconds=3600):
        def decorator(func):
            @self.handle_aws_exceptions
            @wraps(func)
            def wrapper(*args, **kwargs):
                key = serialize_to_ascii((args, kwargs))
                response = self.dynamodb.get_item(TableName=self.cache_table_name, Key={"cache_key": {"S": key}})
                if "Item" in response:
                    cached_data = response["Item"]["cached_data"]["S"]
                    ttl = int(response["Item"]["ttl"]["N"])
                    current_time = int(time.time())
                    if ttl > current_time:
                        return deserialize_from_ascii(cached_data)

                result = func(*args, **kwargs)
                
                serialized_result = serialize_to_ascii(result)
                self.dynamodb.put_item(
                    TableName=self.cache_table_name,
                    Item={
                        "cache_key": {"S": key},
                        "cached_data": {"S": serialized_result},
                        "ttl": {"N": str(int(time.time()) + ttl_seconds)}
                    }
                )
                
                return result
            return wrapper
        return decorator
