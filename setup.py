from setuptools import setup
from pip.req import parse_requirements

requirements = [str(requirement.req) for requirement in parse_requirements('requirements.txt', session='')]

setup(
    name='pokebattle_rl_env',
    version='0.1',
    packages=['pokebattle_rl_env'],
    url='',
    license='',
    author='',
    author_email='',
    description='',
    install_requires=requirements
)
