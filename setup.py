# Copyright 2017 NextThought
# Released under the terms of the LICENSE file.
import codecs
from setuptools import setup, find_packages


version = '4.0.0'

entry_points = {
}

TESTS_REQUIRE = [
    'Acquisition',
    'zope.site',
    'zope.testrunner',
    'testgres',
    'psycopg2-binary; python_implementation != "PyPy"',
]

def _read(fname):
    with codecs.open(fname, encoding='utf-8') as f:
        return f.read()

setup(
    name='nti.testing',
    version=version,
    author='Jason Madden',
    author_email='jason@nextthought.com',
    description="Support for testing code",
    long_description=_read('README.rst') + '\n\n' + _read('CHANGES.rst'),
    license='Apache',
    keywords='nose2 testing zope3 ZTK hamcrest',
    url='https://github.com/OpenNTI/nti.testing',
    project_urls={
        'Documentation': 'https://ntitesting.readthedocs.io/en/latest/',
    },
    classifiers=[
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Software Development :: Testing',
        'Framework :: Zope3',
    ],
    zip_safe=True,
    packages=find_packages('src'),
    package_dir={'': 'src'},
    namespace_packages=['nti'],
    install_requires=[
        'ZODB >= 5.6.0',
        # Error messages changed in 5.1, reprs changed <= 5.4
        'zope.interface >= 5.4.0',
        'pyhamcrest',
        'six',
        'setuptools',
        'transaction',
        'zope.component',
        'zope.configuration',
        'zope.dottedname',
        'zope.exceptions',
        'zope.schema', # schema validation
        'zope.testing',
    ],
    entry_points=entry_points,
    include_package_data=True,
    extras_require={
        'test': TESTS_REQUIRE,
        'docs': [
            'Sphinx',
            'furo',
        ],
        'testgres': [
            'testgres',
            'psycopg2-binary; python_implementation != "PyPy"',
        ],
    },
    python_requires=">=3.8",
)
