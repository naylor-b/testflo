
from distutils.core import setup

setup(name='testflo',
      version='1.0',
      description="A simple flow based testing framework",
      license='Apache 2.0',
      install_requires=[
        'six',
      ],
      packages=['testflo'],
      entry_points="""
          [console_scripts]
          testflo=testflo.main:main
          testflo_pview=testflo.pstats_viewer:main
      """
      )
