from setuptools import setup, find_packages

setup(
    name="attrs-marshmallow",
    version="1.0",
    packages=find_packages("src"),
    package_dir={"": "src"},
    install_requires=["attrs", "marshmallow", "typing_inspect"]
)
