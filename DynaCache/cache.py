import boto3
import logging
import yaml
import time
from botocore.exceptions import BotoCoreError, ClientError
from functools import wraps
import pickle
import binascii

logger = logging.getLogger(__name__)

def serialize_to_ascii(data):
    serialized_data = pickle.dumps(data)
    ascii_str = binascii.hexlify(serialized_data).decode("utf-8")
    return ascii_str

def deserialize_from_ascii(ascii_str):
    binary_data = binascii.unhexlify(ascii_str.encode("utf-8"))
    deserialized_data = pickle.loads(binary_data)
    return deserialized_data

class DynamoDBCache:
    def load_config(self, config_file):
        with open(config_file, "r") as f:
            return yaml.safe_load(f)

    def __init__(self, cache_table_name, defaultTTL=3600, aws_region=None, config_file=None, aws_access_key_id=None, aws_secret_access_key=None, aws_session_token=None):
        self.config = {}
        if config_file:
            self.config = self.load_config(config_file)
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
            raise Exception("Failed to create cache table")
        # self.dynamoTable=self.dynamodb.Table(cache_table_name)
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
                # Handle the error or raise a custom exception here.
        return wrapper

    def cache_response(self, ttl_seconds=3600):
        def decorator(func):
            @self.handle_aws_exceptions
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Serialize the input arguments using the reusable function
                key = serialize_to_ascii((args, kwargs))
                response = self.dynamodb.get_item(TableName=self.cache_table_name, Key={"cache_key": {"S": key}})
                # # Check if the cached item exists and if its TTL has expired
                if "Item" in response:
                    cached_data = response["Item"]["cached_data"]["S"]
                    ttl = int(response["Item"]["ttl"]["N"])
                    current_time = int(time.time())
                    if ttl > current_time:
                        return deserialize_from_ascii(cached_data)

                # If not cached, call the original function
                result = func(*args, **kwargs)
                
                # Serialize the result using the reusable function
                serialized_result = serialize_to_ascii(result)
                # Cache the result with TTL
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
