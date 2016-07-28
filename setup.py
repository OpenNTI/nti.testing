from setuptools import setup, find_packages
import codecs

version = '1.0.0'

entry_points = {
}

TESTS_REQUIRE = [
    'nose2[coverage_plugin]',
    'zope.site',
    'zope.testrunner',
]

def _read(fname):
    with codecs.open(fname, encoding='utf-8') as f:
        return f.read()

setup(
    name = 'nti.testing',
    version = version,
    author = 'Jason Madden',
    author_email = 'jason@nextthought.com',
    description = "Support for testing code",
    long_description = _read('README.rst') + _read('CHANGES'),
    license = 'Apache',
    keywords = 'nose2 testing zope3 ZTK hamcrest',
    url = 'https://github.com/NextThought/nti.testing',
    classifiers = [
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Software Development :: Testing',
        ],
    zip_safe=True,
    packages=find_packages('src'),
    package_dir={'': 'src'},
    namespace_packages=['nti'],
    install_requires=[
        'zope.interface >= 4.1.2', # Listing first to work around a Travis CI issue
        'Acquisition',
        'fudge',
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
    test_suite="nti.testing.tests.test_main.test_suite",
    extras_require={
        'test': TESTS_REQUIRE
    },
)
