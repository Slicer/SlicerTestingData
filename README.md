SlicerTestingData
=================

This is a mirror for the Slicer testing data.

To support content-based addressing, files are uploaded as assets organized in [releases](https://github.com/Slicer/SlicerTestingData/releases)
named after the hashing algorithm.

For each hashing algorithm `<HASHALGO>`, you will find:
* release named `<HASHALGO>`
* markdown document `<HASHALGO>.md` with links of the form `* [<filename>](https://github.com/Slicer/SlicerTestingData/releases/download/<HASHALGO>/<checksum>)`
* a CSV file `<HASHALGO>.csv` listing all `<hashsum>;<filename>` pairs

Upload files
------------

_The commands reported below should be evaluated in the same terminal session. See [Documentation conventions](#documentation-conventions)_

1. Install [Prerequisites](#prerequisites)

2. Copy files to upload in `INCOMING` directory.

```
$ cp /path/to/files/* /path/to/SlicerTestingData/INCOMING
```

3. If needed, create `<HASHALGO>` release

```
$ githubrelease release Slicer/SlicerTestingData create --publish SHA256
```

4. Run update script specifying `<HASHALGO>`, and repeat action for other `<HASHALGO>`.

```
$ /path/to/SlicerTestingData/scripts/update.sh SHA256
```

5. Clear content of `INCOMING` directory if all files have been uploaded for each `<HASHALGO>`.

6. Commit updated `<HASHALGO>.csv` and `<HASHALGO>.md` files

```
$ hashalgo=SHA256
$ git add ${hashalgo}.md ${hashalgo}.csv && \
  git commit -m "Update files associated with ${hashalgo}" && \
  git push origin master
```


Downloading files
-----------------

_The commands reported below should be evaluated in the same terminal session. See [Documentation conventions](#documentation-conventions)_

1. Install [Prerequisites](#prerequisites)

2. Execute download script specifying `<HASHALGO>` to copy the data form

```
$ /path/to/SlicerTestingData/scripts/update.sh SHA256
```


Prerequisites
-------------

_The commands reported below should be evaluated in the same terminal session. See [Documentation conventions](#documentation-conventions)_

1. Download this project

```
$ git clone git://github.com/Slicer/SlicerTestingData
```

2. Install [githubrelease](https://github.com/j0057/github-release#installing)

```
$ pip install githubrelease
```

3. Set `GITHUB_TOKEN` env. variable. Read [here](https://github.com/j0057/github-release#configuring) for more details.

```
$ export GITHUB_TOKEN=YOUR_TOKEN
```


Documentation conventions
-------------------------

Commands to evaluate starts with a dollar sign. For example:

```
$ echo "Hello"
Hello
```

means that `echo "Hello"` should be copied and evaluated in the terminal.
