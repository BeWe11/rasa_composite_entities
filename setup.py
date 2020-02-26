import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="rasa_composite_entities",
    version="1.0.2",
    author="Benjamin Weigang",
    author_email="Benjamin.Weigang@mailbox.org",
    description="A Rasa NLU component for composite entities",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/BeWe11/rasa_composite_entities",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
