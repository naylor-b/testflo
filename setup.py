
from setuptools import setup

setup(name='testflo',
      version='0.1',
      license = 'Apache 2.0',
      zip_safe=False,
      install_requires=[
        'six',
      ],
      packages=['testflo'],
      package_dir={'': 'src'},
      entry_points = {
          "console_scripts": [
                "testflo=testflo.main:main",
              ],
      }
      )
