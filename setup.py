from setuptools import setup

setup(
    name='pool',
    packages=['pool'],
    include_package_data=True,
    install_requires=[
        'Flask',
        'flask_sqlalchemy',
        'wtforms',
        'apscheduler',
        'requests',
    ]
)
