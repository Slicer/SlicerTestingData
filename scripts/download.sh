#/usr/bin/env bash

set -e
set -o pipefail

declare -A hashcmds=()
hashcmds["MD5"]="md5sum"
hashcmds["SHA224"]="sha224sum"
hashcmds["SHA256"]="sha256sum"
hashcmds["SHA384"]="sha384sum"
hashcmds["SHA512"]="sha512sum"

PROG=$(basename $0)

script_dir=$(cd $(dirname $0) || exit 1; pwd)
root_dir=$(realpath ${script_dir}/..)

#------------------------------------------------------------------------------
if ! command -v github-release &> /dev/null; then
	echo >&2 'error: "github-release" not found!'
	exit 1
fi

#------------------------------------------------------------------------------
err() { echo -e >&2 ERROR: $@\\n; }
die() { err $@; exit 1; }
help() {
  cat >&2 <<ENDHELP
Usage: $PROG HASHALGO
Download files associated with HASHALGO release into directory ${root_dir}/HASHALGO/

ENDHELP
}

hashalgo=$1
if [[ "${hashalgo}" == "" ]]; then
  err Missing HASHALGO option
  help
  exit 1
fi

hashcmd=${hashcmds[${hashalgo}]}
if ! command -v ${hashcmd} &> /dev/null; then
	echo >&2 'error: "${hashcmd}" not found!'
	exit 1
fi

if [[ ! -d ${root_dir}/INCOMING ]]; then
  err Missing ${root_dir}/INCOMING directory
  exit 1
fi

if [[ ! -d ${root_dir}/${hashalgo} ]]; then
  err Missing ${root_dir}/${hashalgo} directory
  exit 1
fi

if [[ ! -f ${root_dir}/${hashalgo}.csv ]]; then
  err Missing ${root_dir}/${hashalgo}.csv file
  exit 1
fi

#------------------------------------------------------------------------------
echo "${hashalgo}: downloading release assets"
pushd ${root_dir}/${hashalgo} > /dev/null
for line in $(cat ${root_dir}/${hashalgo}.csv); do
  checksum=$(echo ${line} | cut -d";" -f1)
  filename=$(echo ${line} | cut -d";" -f2)
  download=1
  if [[ -f ${checksum} ]]; then
    current_checksum=$(${hashcmd} ${checksum} | awk '{ print $1 }')
    if [[ ${checksum} == ${current_checksum} ]]; then
      download=0
    fi
  fi
  if [[ $download -eq 1 ]]; then
    githubrelease asset Slicer/SlicerTestingData download SHA256 ${checksum}
    echo
  else
    echo "${hashalgo}: skipping download ${checksum}"
  fi
done
popd > /dev/null
echo

#------------------------------------------------------------------------------
echo "${hashalgo}: copying back to INCOMING directory"
for line in $(cat ${root_dir}/${hashalgo}.csv); do
  checksum=$(echo ${line} | cut -d";" -f1)
  filename=$(echo ${line} | cut -d";" -f2)
  echo "${hashalgo}: copying ${filename}"
  cp ${root_dir}/${hashalgo}/${checksum} ${root_dir}/INCOMING/${filename}
done

