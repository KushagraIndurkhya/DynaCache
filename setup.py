from setuptools import setup

setup(
    name='DynaCache',
    version='0.1.0.4',
    description='DynaCache: Effortlessly cache function responses in DynamoDB for lightning-fast, efficient data retrieval.',
    author='Kushagra Indurkhya',
    author_email='kushagraindurkhya7@gmail.com',
    url='https://github.com/KushagraIndurkhya/DynaCache',
    packages=['DynaCache'],
    install_requires=[
        'PyYAML>=5.4.1',  # Configuration file parsing
    ],
)