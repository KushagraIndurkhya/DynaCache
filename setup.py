from setuptools import setup

setup(
    name='DynaCache',
    version='0.1.0',
    description='DynaCache: Effortlessly cache function responses in DynamoDB for lightning-fast, efficient data retrieval.',
    author='Kushagra Indurkhya',
    author_email='kindurkhya7@gmail.com',
    url='https://github.com/KushagraIndurkhya/DynaCache',
    packages=['DynaCache'],
    install_requires=[
        'boto3>=1.18.0',  # DynamoDB interaction
        'PyYAML>=5.4.1',  # Configuration file parsing
    ],
)