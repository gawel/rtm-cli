from setuptools import setup, find_packages

version = '0.1'

setup(name='rtm-cli',
      version=version,
      description="Read The Milk Client",
      long_description="""\
""",
      classifiers=[],
      keywords='rtm cli',
      author='Gael Pasgrimaud',
      author_email='gael@gawel.org',
      url='',
      license='MIT',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          # -*- Extra requirements: -*-
          'pyrtm',
          'docopt',
          'couleur',
      ],
      entry_points="""
      # -*- Entry points: -*-
      [console_scripts]
      rtm = rtmcli.main:main
      """,
      )
