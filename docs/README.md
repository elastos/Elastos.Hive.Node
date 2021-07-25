## Hive Node Document Specification

#### Preparation

To generate the document of the Hive Node, please run the test cases first: (Assume the directory of the hive source is HIVE_SOURCE_ROOT)

```shell script
$ cd <HIVE_SOURCE_ROOT>
$ ./run.sh test
```

Then install the packages for document generation:

```shell script
$ cd <HIVE_SOURCE_ROOT>
$ source .venv/bin/activate
$ pip install -U sphinx
$ pip install sphinxcontrib_httpdomain
$ pip install sphinx-rtd-theme
```

#### Generate the document

```shell script
$ cd <HIVE_SOURCE_ROOT>/docs
$ PYTHONPATH="${PYTHONPATH}:<HIVE_SOURCE_ROOT>:<HIVE_SOURCE_ROOT>/.venv/lib/python3.8/site-packages" sphinx-build -b html source build
```

The index of the document is located under <HIVE_SOURCE_ROOT>/docs/build/index.html.
