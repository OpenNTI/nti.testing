# Copyright 2017 NextThought
# Released under the terms of the LICENSE file.
import codecs
from setuptools import setup, find_packages


version = '3.1.0'

entry_points = {
}

TESTS_REQUIRE = [
    'Acquisition',
    'zope.site',
    'zope.testrunner',
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
    url='https://github.com/NextThought/nti.testing',
    project_urls={
        'Documentation': 'https://ntitesting.readthedocs.io/en/latest/',
    },
    classifiers=[
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
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
            'sphinx_rtd_theme',
        ],
        ':python_version == "2.7"' : [
            # backport of unittest.mock for Python 2.7.
            'mock',
        ],
    },
)
