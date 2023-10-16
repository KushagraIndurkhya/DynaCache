# DynaCache

DynaCache is a Python library that simplifies caching data in Amazon DynamoDB, a managed NoSQL database service provided by AWS.

With DynaCache, you can easily store and retrieve function results as a way to optimize your applications and reduce latency by caching frequently requested data. This library is particularly useful for scenarios where you want to speed up repetitive or computationally expensive operations by storing their results in DynamoDB for quick retrieval.

## Features

- **DynamoDB Integration**: DynaCache seamlessly integrates with AWS DynamoDB, a highly available and scalable NoSQL database service.
- **Automatic TTL Management**: It manages Time-To-Live (TTL) for cached data, ensuring that stale data is automatically removed from the cache.
- **Customizable**: You can specify your own Time-To-Live (TTL) for cached items, or use the default value of 1 hour.
- **Class Function Support**: You can cache the results of class functions, including static and class methods.
- **Serialization**: The library uses serialization to cache function results and deserialize them when retrieving cached data.
- **Easy Configuration**: You can configure DynaCache through a YAML configuration file or directly provide AWS credentials and region.

## Installation

You can install DynaCache using `pip`:

```bash
pip install dynacache
```

## Usage
Below is some sample code using DynaCache:

```python
from dynacache import DynamoDBCache

# Initialize DynamoDBCache
cache = DynamoDBCache(
    cache_table_name="MyCacheTable",
    aws_region="us-east-1",
    aws_access_key_id="your-access-key",
    aws_secret_access_key="your-secret-key"
)

# Define a function you want to cache
@cache.cache_response(ttl_seconds=3600)  # Cache results for 1 hour
def expensive_function(x, y):
    # Your expensive computation here
    return x + y

# Call the cached function
result = expensive_function(3, 4)  # The result is cached for subsequent calls

```

### Configuration
You can configure DynaCache by providing AWS credentials and region directly, or by using a configuration file. Here's how to set up the configuration file:

```yaml
# config.yaml
aws_region: us-east-1
aws_access_key_id: your-access-key
aws_secret_access_key: your-secret-key
```
Then, you can initialize DynamoDBCache using this configuration file:

```python
cache = DynamoDBCache(cache_table_name="MyCacheTable", config_file="config.yaml")

```

### Default boto setup

If no AWS credentials are provided, DynaCache will try to use the default credential chain provided by boto3. This means it will look for credentials in the environment variables, shared credentials file, EC2 IAM role etc. For more information, see [Boto3 documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html#credentials).

## License
DynaCache is released under the MIT license.
See LICENSE for more details.

## Contributing
This project is a basic implementation of a caching library for DynamoDB, and is open source. Feel free to submit issues or pull requests to improve it.

Contributions are welcome! Please submit a pull request with your changes. When doing so, please follow the existing code style and conventions. And add/update tests for any new functionality.

To contribute:
1. Fork the repository
2. Create a new branch for your changes:
```bash
git checkout -b your-branch-name
```
3. Make and test your changes
4. Add new features and tests

Disclaimer: DynaCache is not an official product or library provided by AWS. It is a third-party library developed to simplify the process of caching data in AWS DynamoDB.