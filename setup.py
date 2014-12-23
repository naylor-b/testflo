
from setuptools import setup, find_packages

setup(name='testflo',
      version='0.1',
      license = 'Apache 2.0',
      zip_safe=False,
      packages=find_packages('src'),
      package_dir={'': 'src'},
      entry_points = {
          "console_scripts": [
                "testflo=testflo.testflo:run_tests",
              ],
      }
      )
