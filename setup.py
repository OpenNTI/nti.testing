# Copyright 2017 NextThought
# Copyright 2022-2024 Jason Madden
# Released under the terms of the LICENSE file.
import codecs
from setuptools import setup
from setuptools import find_namespace_packages


version = '4.6.0'

entry_points = {
}

TESTS_REQUIRE = [
    'Acquisition',
    'zope.testrunner',
    'testgres >= 1.11',
    'psycopg2-binary',
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
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Programming Language :: Python :: 3.14',
        'Programming Language :: Python :: 3.15',
        'Programming Language :: Python :: Implementation :: CPython',
        'Topic :: Software Development :: Testing',
        'Framework :: Zope3',
    ],
    zip_safe=True,
    packages=find_namespace_packages(where='src'),
    package_dir={'': 'src'},
    install_requires=[
        # Error messages changed in 5.1, reprs changed <= 5.4
        'zope.interface >= 5.4.0',
        'pyhamcrest',
        'six',
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
        'zodb': [
            'ZODB >= 5.6.0',
        ],
        'test': TESTS_REQUIRE,
        'test-zodb': [
            'zope.site',
        ],
        'docs': [
            'Sphinx',
            'furo',
        ] + TESTS_REQUIRE,
        'testgres': [
            'testgres >= 1.11',
            # 1.14.4 is the last release before testgres adapted the
            # "internal_platform_utils" concept. 1.15.x and 1.16.[01] don't
            # provide an implementation that works on macOS, leading to
            # NotImplementedError exceptions. We can either
            # pin to an old version on macOS like this::
            #
            # 'testgres >= 1.11; platform_system != "Darwin"',
            # 'testgres == 1.14.4; platform_system == "Darwin"',
            #
            # Or we can attempt a work-around in code. Currently, we're
            # attempting a workaround in code.
        ],
    },
    python_requires=">=3.11",
)
