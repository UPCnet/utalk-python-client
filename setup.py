from setuptools import setup, find_packages

version = '1.2.dev0'

setup(name='utalk-python-client',
      version=version,
      description="UTalk Python Client",
      long_description="""\
A STOMP-trough-websockets python implementation for the UTalk service""",
      classifiers=[],  # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='',
      author='Carles Bruguera',
      author_email='carles.bruguera@upcnet.es',
      url='https://github.com/UPCnet/utalk-python-client',
      license='',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          # -*- Extra requirements: -*-
          'setuptools',
          'ipdb',
          'docopt',
          'maxcarrot',
          'stomp.py',
          'ws4py',
          'wsaccel',
          'gevent'

      ],
      entry_points="""
      # -*- Entry points: -*-
      [console_scripts]
      utalk = utalkpythonclient:main
      """,
      )
