#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script to download release files or upload new files in INCOMING folder as release files.
It can be run from the command-line.

Requires `githubrelease` package to be installed, installable with ``pip install githubrelease``.

Download SHA256 hashed files to DOWNLOAD folder::

    python process_release_data.py download --hashalgo SHA256 --github-token 123123...123

Upload all hashes from INCOMING folder::

    python process_release_data.py upload --github-token 123123...123

Show detailed help::

    python process_release_data.py -h

"""


import os, sys
import logging
import github_release
from shutil import copyfile


COLUMN_CHECKSUM = 0
COLUMN_FILENAME = 1
COLUMN_FILEDATE = 2
COLUMN_LOCAL_FILENAME = 3

DEFAULT_FILE_DATE_UTC_STRING="2020-01-01T12:00:00.0Z"

def get_hashcmd(hashalgo):
    """Get function that can compute hash for a filename"""
    import hashlib

    if hashalgo == "MD5":
        return lambda filename: hashlib.md5(open(filename, "rb").read()).hexdigest()
    elif hashalgo == "SHA224":
        return lambda filename: hashlib.sha224(open(filename, "rb").read()).hexdigest()
    if hashalgo == "SHA256":
        return lambda filename: hashlib.sha256(open(filename, "rb").read()).hexdigest()
    if hashalgo == "SHA384":
        return lambda filename: hashlib.sha384(open(filename, "rb").read()).hexdigest()
    if hashalgo == "SHA512":
        return lambda filename: hashlib.sha512(open(filename, "rb").read()).hexdigest()
    else:
        return None


class cd:
    """Context manager for changing the current working directory"""

    def __init__(self, newPath):
        self.newPath = os.path.expanduser(newPath)

    def __enter__(self):
        self.savedPath = os.getcwd()
        os.chdir(self.newPath)

    def __exit__(self, etype, value, traceback):
        os.chdir(self.savedPath)


def download_fileindex_csv(repo_name, download_dir, hashalgo, github_token=None):
    if github_token:
        github_release._github_token_cli_arg = github_token
    fileindex_csv = os.path.join(download_dir, hashalgo + ".csv")
    if os.path.isfile(fileindex_csv):
        os.remove(fileindex_csv)
    with cd(download_dir):
        if not github_release.gh_asset_download(repo_name, hashalgo, hashalgo + ".csv"):
            raise ValueError("Failed to download " + hashalgo + ".csv")
    return fileindex_csv


def read_fileindex_csv(hashalgo_csv):
    fileindex = []
    with open(hashalgo_csv, "r") as f:
        for line in f:
            fields = line.rstrip().split(";")
            if len(fields) <= COLUMN_FILEDATE:
                fields.append("")  # if date is missing then add an empty field
            fileindex.append(fields)
    return fileindex


def write_fileindex_csv(hashalgo_csv, fileindex):
    with open(hashalgo_csv, "wb") as f:
        for fileindex_item in fileindex:
            fields = [fileindex_item[COLUMN_CHECKSUM], fileindex_item[COLUMN_FILENAME]]
            if len(fileindex_item) > COLUMN_FILEDATE:
                fields.append(fileindex_item[COLUMN_FILEDATE])
            f.write(bytes(";".join(fields) + "\n", "UTF-8"))


def write_fileindex_md(hashalgo_md, fileindex, repo_name, hashalgo, format=None, include_local_filename=False):
    """Write file index as markdown.
    format: list or table
    """
    if format is None:
        format = "list"
    with open(hashalgo_md, "wb") as f:
        if format=="table":
            header = []
            header.append("| FileName | FileDate | " + hashalgo + " |\n")
            header.append("|----------|----------|-------------|\n")
            if include_local_filename:
                header[0] = "| LocalFileName " + header[0]
                header[1] = "|---------------" + header[1]
            for header_line in header:
                f.write(bytes(header_line, "UTF-8"))
        for fileindex_item in fileindex:
            checksum = fileindex_item[COLUMN_CHECKSUM]
            filename = fileindex_item[COLUMN_FILENAME]
            filedate = fileindex_item[COLUMN_FILEDATE] if len(fileindex_item) > COLUMN_FILEDATE else ""
            local_filename = fileindex_item[COLUMN_LOCAL_FILENAME] if len(fileindex_item) > COLUMN_LOCAL_FILENAME else ""
            if format=="table":
                row = ""
                if include_local_filename:
                    row += "| " + local_filename + " "
                row += "| [" + filename + "](https://github.com/" + repo_name + "/releases/download/" + hashalgo + "/" + checksum + ") "
                row += "| " + filedate + " "
                row += "| " + checksum + " "
                f.write(bytes(row + "|\n", "UTF-8",))
            else:
                f.write(bytes("- [" + filename + "](https://github.com/" + repo_name + "/releases/download/" + hashalgo + "/" + checksum + ")\n", "UTF-8",))
                if include_local_filename:
                    f.write(bytes("  - LocalFileName: " + local_filename + "\n", "UTF-8",))
                if filedate:
                    f.write(bytes("  - FileDate: " + filedate + "\n", "UTF-8",))
                f.write(bytes("  - " + hashalgo +": " + checksum + "\n", "UTF-8",))


def get_filedate(filepath):
    # Return
    import datetime
    return datetime.datetime.utcfromtimestamp(os.path.getmtime(filepath)).replace(tzinfo=datetime.timezone.utc)

def set_filedate(filepath, filedate):
    stat = os.stat(filepath)
    atime = stat.st_atime
    os.utime(filepath, (atime, filedate.timestamp()))

def date_to_utc_string(filedate):
    """Convert date object to string in UTC time zone"""
    return filedate.isoformat()

def date_from_utc_string(filedate_utc_string):
    """Convert string in UTC time zone to date object"""
    # We only accept date in UTC (indicated by +00:00 or Z suffix)
    import datetime
    try:
        date_object = datetime.datetime.strptime(filedate_utc_string, "%Y-%m-%dT%H:%M:%S.%f+00:00").replace(tzinfo=datetime.timezone.utc)
    except ValueError:
        date_object = datetime.datetime.strptime(filedate_utc_string, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=datetime.timezone.utc)
    return date_object


def download(repo_name, root_dir, download_dir, hashalgo, github_token=None):
    """Download files associated with HASHALGO release into directory (root_dir)/(hashalgo).
  List of files is taken from (root_dir)/(hashalgo).csv. If multiple hashes associated with
  the same filename then the last entry will be used.
  """

    if github_token:
        github_release._github_token_cli_arg = github_token

    if not os.path.isdir(download_dir):
        os.mkdir(download_dir)

    hashalgo_dir = os.path.join(root_dir, hashalgo)
    if not os.path.isdir(hashalgo_dir):
        os.mkdir(hashalgo_dir)

    hashalgo_csv = download_fileindex_csv(
        repo_name, hashalgo_dir, hashalgo, github_token
    )
    fileindex = read_fileindex_csv(hashalgo_csv)

    logging.debug(hashalgo + ": downloading release assets")
    # Find out which filenames are present in multiple versions (need to give them unique names)
    filenames = [checksum_filename[1] for checksum_filename in fileindex]
    from collections import Counter

    # Sort based on filename and filedate
    fileindex.sort(key=lambda a: (a[COLUMN_FILENAME].casefold(), a[COLUMN_FILEDATE]))

    filenames_counter = Counter(filenames)
    # download saves files to current working directory, so we need to temporarily
    # change working dir to hashalgo_dir folder
    with cd(hashalgo_dir):
        fileindex_with_local_filename = []
        for fileindex_item in fileindex:
            checksum = fileindex_item[COLUMN_CHECKSUM]
            filename = fileindex_item[COLUMN_FILENAME]
            filedate = fileindex_item[COLUMN_FILEDATE] if len(fileindex_item) > COLUMN_FILEDATE else ""
            filepath = os.path.join(hashalgo_dir, checksum)
            if not os.path.isfile(filepath):
                if not github_release.gh_asset_download(repo_name, hashalgo, checksum):
                    logging.error(
                        hashalgo
                        + ": failed to download "
                        + filename
                        + " ("
                        + checksum
                        + ")"
                    )
                    continue
                logging.debug(
                    hashalgo + ": downloaded " + filename + " (" + checksum + ")"
                )

            # determine local filename
            if filenames_counter[filename] == 1:
                # unique filename
                local_filename = filename
            else:
                # multiple versions of the filename with different content
                # add checksum as suffix to distinguish them
                local_filename = filename + "." + checksum
            local_filepath = os.path.join(download_dir, local_filename)

            # set file name and date from index
            copyfile(filepath, local_filepath)
            set_filedate(local_filepath, date_from_utc_string(filedate if filedate else DEFAULT_FILE_DATE_UTC_STRING))

            # save local fileindex
            fileindex_with_local_filename.append([checksum, filename, filedate, local_filename])

        # Create new hashalgo.csv from existing and incoming files
        write_fileindex_csv(hashalgo_csv, fileindex)
        hashalgo_local_md = os.path.join(download_dir, hashalgo + "_local.md")
        write_fileindex_md(hashalgo_local_md, fileindex_with_local_filename, repo_name, hashalgo, include_local_filename=True)


def upload(repo_name, root_dir, incoming_dir, hashalgo, github_token=None):
    """Upload incoming files associated them with hashalgo release."""

    if github_token:
        github_release._github_token_cli_arg = github_token

    hashcmd = get_hashcmd(hashalgo)
    if not hashcmd:
        raise ValueError('hashalgo "' + hashalgo + '" not found')

    if not os.path.isdir(incoming_dir):
        raise ValueError("Missing " + incoming_dir + " directory")

    hashalgo_dir = os.path.join(root_dir, hashalgo)
    if not os.path.isdir(hashalgo_dir):
        os.mkdir(hashalgo_dir)

    # Download information about current release

    # Get current fileindex
    try:
        hashalgo_csv = download_fileindex_csv(
            repo_name, hashalgo_dir, hashalgo, github_token
        )
        fileindex = read_fileindex_csv(hashalgo_csv)
    except ValueError:
        # New release
        hashalgo_csv = os.path.join(hashalgo_dir, hashalgo + ".csv")
        fileindex = []

    # Get list of successfully uploaded assets (to avoid uploading them again)
    # and delete partially uploaded ones.
    uploaded_assets = (
        github_release.get_assets(repo_name, hashalgo) if fileindex else []
    )
    uploaded_hashes = []
    for asset in uploaded_assets:
        if asset["state"] == "uploaded":
            uploaded_hashes.append(asset["name"])
        else:
            # Remove asset partially uploaded
            github_release.gh_asset_delete(repo_name, hashalgo, asset["name"])

    # Update release information with incoming data

    # Add incoming files to fileindex and hashalgo_dir
    filenames = [
        f
        for f in os.listdir(incoming_dir)
        if os.path.isfile(os.path.join(incoming_dir, f)) and not f.startswith(".")
    ]
    for filename in filenames:
        filepath = os.path.join(incoming_dir, filename)
        checksum = hashcmd(filepath)
        filedate = date_to_utc_string(get_filedate(filepath))

        existingItems = [fileindex_item for fileindex_item in fileindex
            if fileindex_item[COLUMN_CHECKSUM] == checksum and fileindex_item[COLUMN_FILENAME] == filename]
        if not existingItems:
            # new item
            fileindex.append([checksum, filename, filedate])
        # Make sure the hash-named file is present
        hashfilepath = os.path.join(hashalgo_dir, checksum)
        if not os.path.isfile(hashfilepath):
            copyfile(filepath, hashfilepath)

    # Create new hashalgo.csv from existing and incoming files
    fileindex.sort(key=lambda a: (a[COLUMN_FILENAME].casefold(), a[COLUMN_FILEDATE]))
    write_fileindex_csv(hashalgo_csv, fileindex)
    hashalgo_md = os.path.join(root_dir, hashalgo_dir, hashalgo + ".md")
    write_fileindex_md(hashalgo_md, fileindex, repo_name, hashalgo)

    # Upload updated releaes info and new data files

    # Create hashalgo release (in case it does not exist)
    github_release.gh_release_create(repo_name, hashalgo, publish=True)

    # Delete old hashalgo.csv and hashalgo.md
    github_release.gh_asset_delete(repo_name, hashalgo, hashalgo + ".csv")
    github_release.gh_asset_delete(repo_name, hashalgo, hashalgo + ".md")

    # Upload new hashalgo.csv and hashalgo.md
    github_release.gh_asset_upload(repo_name, hashalgo, hashalgo_csv)
    github_release.gh_asset_upload(repo_name, hashalgo, hashalgo_md)

    # Upload new data files
    for fileindex_item in fileindex:
        checksum = fileindex_item[COLUMN_CHECKSUM]
        filename = fileindex_item[COLUMN_FILENAME]
        if checksum in uploaded_hashes:
            # already uploaded
            continue
        filepath = os.path.join(hashalgo_dir, checksum)
        github_release.gh_asset_upload(repo_name, hashalgo, filepath)

    # Copy md file content into release notes
    with open(hashalgo_md, "r") as file:
        release_notes = file.read()

    if len(release_notes) > 125000:
        note = "Since the release description is > 125000 characters, the corresponding markdown file is instead pushed into the repository."
        release_notes = f"See [{hashalgo}.md](https://github.com/{repo_name}/blob/main/{hashalgo}/{hashalgo}.md)\n\n_{note}_"
        logging.warning(f"{hashalgo}: {note}")

    github_release.gh_release_edit(repo_name, hashalgo, body=release_notes)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Downloads release files or uploads new files in INCOMING folder as release assets."
    )
    parser.add_argument(
        "operation",
        help="operation to perform. Valid values: download, upload. Upload adds all files in INCOMING folder. Download gets all files in the .csv index to (hash-algo)-DOWNLOAD folder.",
    )
    parser.add_argument(
        "--hash-algo",
        help="hashing algorithm name. If not specified then SHA256 is used. Valid values: MD5, SHA256, SHA224, SHA384, SHA512.",
    )
    parser.add_argument(
        "--github-token",
        help="github personal access token. If not specified here then it must be set in GITHUB_TOKEN environment variable.",
    )
    parser.add_argument(
        "--github-repo",
        help="github repository (default: Slicer/SlicerTestingData)",
        default="Slicer/SlicerTestingData",
    )

    args = parser.parse_args()
    repo_name = args.github_repo
    github_token = args.github_token
    operation = args.operation
    root_dir = os.path.dirname(os.path.realpath(__file__))

    if operation == "download":
        hashalgo = args.hash_algo if args.hash_algo else "SHA256"
        download_dir = os.path.join(root_dir, hashalgo + "-DOWNLOAD")
        download(repo_name, root_dir, download_dir, hashalgo, github_token)
    elif operation == "upload":
        incoming_dir = os.path.join(root_dir, "INCOMING")
        hashalgos = [args.hash_algo] if args.hash_algo else ["SHA256"]
        for hashalgo in hashalgos:
            logging.info("Uploading " + hashalgo)
            upload(repo_name, root_dir, incoming_dir, hashalgo, github_token)
    else:
        parser.print_help()
        exit(1)
