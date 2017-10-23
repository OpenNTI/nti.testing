# Copyright 2017 NextThought
# Released under the terms of the LICENSE file.
import codecs
from setuptools import setup, find_packages


version = '2.1.0'

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
    classifiers=[
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
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
        'zope.interface >= 4.1.2', # Listing first to work around a Travis CI issue
        'pyhamcrest',
        'six',
        'setuptools',
        'transaction',
        'zope.component',
        'zope.configuration',
        'zope.dottedname',
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
