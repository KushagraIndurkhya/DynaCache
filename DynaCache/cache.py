import json
import boto3
import logging
import yaml
import time
from botocore.exceptions import BotoCoreError, ClientError
from functools import wraps
import pickle

logger = logging.getLogger(__name__)

class DynamoDBCache:
    def load_config(self, config_file):
        with open(config_file, "r") as f:
            return yaml.safe_load(f)
    def __init__(self,cache_table_name,defaultTTL=3600,aws_region=None,config_file=None, aws_access_key_id=None, aws_secret_access_key=None, aws_session_token=None):
        self.config={}
        if config_file:
            self.config = self.load_config(config_file)
        self.aws_access_key_id = aws_access_key_id or self.config.get("aws_access_key_id")
        self.aws_secret_access_key = aws_secret_access_key or self.config.get("aws_secret_access_key")
        self.aws_session_token = aws_session_token or self.config.get("aws_session_token")
        self.aws_region = aws_region or self.config["aws_region"]
        self.cache_table_name = cache_table_name
        self.dynamodb = self.setup_dynamodb()
        try:
            self.create_cache_table()
        except Exception as e:
            raise Exception("Failed to create cache table")
        # self.dynamoTable=self.dynamodb.Table(cache_table_name)
        self.defaultTTL=defaultTTL


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
                    },
                    {
                        "AttributeName": "ttl",
                        "AttributeType": "N"  # Numeric attribute for TTL
                    }
                ],
                ProvisionedThroughput={
                    "ReadCapacityUnits": 5,
                    "WriteCapacityUnits": 5
                },
                TimeToLiveSpecification={
                    "AttributeName": "ttl",  # Specify the TTL attribute name
                    "Enabled": True           # Enable TTL for the table
                }
            )
            self.dynamodb.get_waiter('table_exists').wait(TableName=self.cache_table_name)
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
                key = f"{func.__name__}-{pickle.dumps((args, kwargs))}"
                response = self.dynamodb.get_item(TableName=self.cache_table_name, Key={"cache_key": {"S": key}})
                
                # Check if the cached item exists and if its TTL has expired
                if "Item" in response:
                    cached_data = response["Item"]["cached_data"]["S"]
                    ttl = int(response["Item"]["ttl"]["N"])
                    current_time = int(time.time())

                    if ttl > current_time:
                        # Cache is still valid, return the cached data
                        return pickle.loads(cached_data)

                # If not cached or expired, call the original function
                result = func(*args, **kwargs)
                
                # Cache the result with a new TTL
                self.dynamodb.put_item(
                    TableName=self.cache_table_name,
                    Item={
                        "cache_key": {"S": key},
                        "cached_data": {"S": pickle.dumps(result)},
                        "ttl": {"N": str(current_time + ttl_seconds)}
                    }
                )
                
                return result
            return wrapper
        return decorator
