## Hive Node Document Specification

#### Preparation

To generate the document of the Hive Node, please run the test cases first: (Assume the directory of the hive source is HIVE_SOURCE_ROOT)

```shell script
$ ./run.sh setup
```

Then install the packages for document generation:

```shell script
$ source .venv/bin/activate
$ pip install -U sphinx
$ pip install sphinxcontrib_httpdomain
$ pip install sphinx-rtd-theme
```

#### Generate the document

```shell script
# Replace the HIVE_SOURCE_ROOT with the full path of the hive node source codes.
# Please check the folder python3.9 and get the corrected one.
$ cd docs
$ PYTHONPATH="${PYTHONPATH}:<HIVE_SOURCE_ROOT>:<HIVE_SOURCE_ROOT>/.venv/lib/python3.9/site-packages" sphinx-build -b html source build
```

The index of the document is located under <HIVE_SOURCE_ROOT>/docs/build/index.html.
