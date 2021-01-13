import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="rasa_composite_entities",
    version="2.0.1",
    author="Benjamin Weigang",
    author_email="Benjamin.Weigang@mailbox.org",
    description="A Rasa NLU component for composite entities",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/BeWe11/rasa_composite_entities",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
