from setuptools import setup

setup(
    name='mail_export',
    version='0.0.1',
    packages=['richlog', 'exchange', 'mail_export'],
    install_requires=open('requirements.txt').read().split('\n'),
    url='',
    license='MIT',
    author='Daniel Engvall',
    author_email='daniel@engvalls.eu',
    description='An application for exporting existing emails',
    entry_points={
        'console_scripts': ['mail_export=mail_export.__main__:main']
    }
)
