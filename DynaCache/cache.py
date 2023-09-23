import json
import boto3
import logging
import yaml
import time
from botocore.exceptions import BotoCoreError, ClientError
from functools import wraps

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
                    }
                ],
                ProvisionedThroughput={
                    "ReadCapacityUnits": 5,
                    "WriteCapacityUnits": 5
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
                # Generate a unique key based on function name and input parameters
                key = f"{func.__name__}-{json.dumps((args, kwargs))}"
                # Check if the result is cached
                response = self.dynamodb.get_item(TableName=self.cache_table_name, Key={"cache_key": {"S": key}})
                if "Item" in response:
                    cached_data = response["Item"]["cached_data"]["S"]
                    return json.loads(cached_data)

                # If not cached, call the original function
                result = func(*args, **kwargs)
                # Cache the result with TTL
                self.dynamodb.put_item(
                    TableName=self.cache_table_name,
                    Item={
                        "cache_key": {"S": key},
                        "cached_data": {"S": json.dumps(result)},
                        "ttl": {"N": str(int(time.time()) + ttl_seconds)}
                    }
                )

                return result

            return wrapper

        return decorator


# if __name__ == "__main__":
#     cache_instance=DynamoDBCache(cache_table_name="test-Cache",aws_region="ap-south-1")
#     @cache_instance.cache_response(ttl_seconds=40)
#     def test(a,b,c):
#         time.sleep(3)
#         return a+b+c
#     d=test(2,3,5)
#     e=test(2,3,5)
    

