from setuptools import find_packages, setup


setup(
    name="tabletop-lab",
    version="0.1.0",
    description="Reusable simulation framework for small tabletop card and token games.",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
)
