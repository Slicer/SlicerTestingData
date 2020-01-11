SlicerTestingData
=================

This is a mirror for storing Slicer testing data.

To support content-based addressing, files are uploaded as assets organized in [releases](https://github.com/Slicer/SlicerTestingData/releases)
named after the hashing algorithm.

For each hashing algorithm `<HASHALGO>` (MD5, SHA256, ...), you will find:
* release named `<HASHALGO>`
* markdown document `<HASHALGO>.md` with links of the form `* [<filename>](https://github.com/Slicer/SlicerTestingData/releases/download/<HASHALGO>/<checksum>)`
* a CSV file `<HASHALGO>.csv` listing all `<hashsum>;<filename>` pairs

_The commands reported below should be evaluated in the same terminal session. See [Documentation conventions](#documentation-conventions)_

Upload files
------------

1. Install [Prerequisites](#prerequisites)

2. Copy files to upload in `INCOMING` directory.

3. Run process_release_data.py script specifying your github token and upload command.

```
$ python process_release_data.py upload --github-token 123123...123
```

4. Optional: Clear content of `INCOMING` directory if all files have been uploaded for each `<HASHALGO>`.


Downloading files
-----------------

1. Install [Prerequisites](#prerequisites)

2. Run process_release_data.py script specifying your github token, download command, and hash algorithm. If multiple versions of the same filename are uploaded then the unique file names will be generated in the download folder by attaching the checksum to the end of each original filename.

```
$ python process_release_data.py download --github-token 123123...123
```


Prerequisites
-------------

1. Download this project

```
$ git clone git://github.com/Slicer/SlicerTestingData
```

2. Install Python and [githubrelease](https://github.com/j0057/github-release#installing) package

```
$ pip install githubrelease
```

3. [Create a github personal access token](https://help.github.com/articles/creating-an-access-token-for-command-line-use) with "repo" scope to get read/write access to the repository


Documentation conventions
-------------------------

Commands to evaluate starts with a dollar sign. For example:

```
$ echo "Hello"
Hello
```

means that `echo "Hello"` should be copied and evaluated in the terminal.
