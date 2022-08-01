## Hive Node Document Specification

#### Preparation

To generate the document of the Hive Node, please run the test cases first: (Assume the directory of the hive source is HIVE_SOURCE_ROOT)

```shell script
$ ./run.sh setup
```

Then install the packages for document generation:

```shell script
$ source .venv/bin/activate
$ pip install sphinx sphinxcontrib_httpdomain sphinx-rtd-theme werkzeug==2.1.2
```

#### Generate the document

```shell script
$ cd docs
$ ./make.sh
```

The index of the document is located under `build/index.html`.
