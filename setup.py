from os import path, pardir, chdir
from setuptools import setup, find_packages

README = open(path.join(path.dirname(__file__), 'README.rst')).read()
# allow setup.py to be run from any path
chdir(path.normpath(path.join(path.abspath(__file__), pardir)))

setup(
    name="django-side-effects",
    version="1.2.3",
    packages=find_packages(),
    include_package_data=True,
    description='Django app for managing external side effects.',
    long_description=README,
    url='https://github.com/yunojuno/django-side-effects',
    install_requires=[
        'django>=1.11',
        'python-env-utils'
    ],
    author='YunoJuno',
    author_email='code@yunojuno.com',
    license='MIT',
    maintainer='YunoJuno',
    maintainer_email='code@yunojuno.com',
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 1.11',
        'Framework :: Django :: 2.0',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
)
