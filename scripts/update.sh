#/usr/bin/env bash

set -e
set -o pipefail

PROG=$(basename $0)

script_dir=$(cd $(dirname $0) || exit 1; pwd)
root_dir=$(realpath ${script_dir}/..)

declare -A hashcmds=()
hashcmds["MD5"]="md5sum"
hashcmds["SHA224"]="sha224sum"
hashcmds["SHA256"]="sha256sum"
hashcmds["SHA384"]="sha384sum"
hashcmds["SHA512"]="sha512sum"

supported_hashalgos=${!hashcmds[@]}

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
Usage: $PROG HASHALGO [HASHALGO ...]

Upload incoming files associated them with HASHALGO release.
Available HASHALGO are ${supported_hashalgos}

ENDHELP
}

if [[ "$@" == "" ]]; then
  err Missing HASHALGO option
  help
  exit 1
fi
for hashalgo in "$@"; do
  if [[ ! "${supported_hashalgos}" =~ "${hashalgo}" ]]; then
    err Unknown HASHALGO [${hashalgo}] option
    help
    exit 1
  fi
done
hashalgos="$@"

for hashalgo in ${hashalgos}; do
  hashcmd=${hashcmds[${hashalgo}]}
  if ! command -v ${hashcmd} &> /dev/null; then
    echo >&2 'error: "${hashcmd}" not found!'
    exit 1
  fi
done

#------------------------------------------------------------------------------
for hashalgo in ${hashalgos}; do

  hashcmd=${hashcmds[${hashalgo}]}

  mkdir -p ${root_dir}/${hashalgo}

  if [[ ! -f ${root_dir}/${hashalgo}.csv ]]; then
    touch ${root_dir}/${hashalgo}.csv
  fi

  #----
  echo "${hashalgo}: checking for incoming files"
  pushd ${root_dir}/INCOMING > /dev/null
  for filename in $(ls -1  | sort); do
    echo "${hashalgo}: found ${filename}"
    checksum=$(${hashcmd} ${filename} | awk '{ print $1 }')
    cp ${filename} ${root_dir}/${hashalgo}/${checksum}
    referenced_assets=$(cat ${root_dir}/${hashalgo}.csv | cut -d";" -f1)
    if [[ ! "${referenced_assets}" =~ "${checksum}" ]]; then
      echo "${checksum};${filename}" >> ${root_dir}/${hashalgo}.csv
    fi
  done
  popd > /dev/null
  echo

  #----
  echo "${hashalgo}: retrieving list of uploaded assets"
  set +o pipefail
  uploaded_assets=$(
    githubrelease asset Slicer/SlicerTestingData list ${hashalgo}  | tr -d " " | grep name -A1 | sed -e "s/name://" | sed -e "s/state://" | grep -v  -E "\-\-" | while read checksum
    do
      read upload_state
      if [[ ${upload_state} == "uploaded" ]]; then
        echo ${checksum}
      else
        # Remove asset partially uploaded
        githubrelease asset Slicer/SlicerTestingData delete ${hashalgo} ${checksum}
      fi
    done
  )
  set -o pipefail
  echo

  rm -f ${root_dir}/${hashalgo}.md

  #----
  echo "${hashalgo}: uploading release assets"
  echo "| FileName | ${hashalgo} |" >> ${root_dir}/${hashalgo}.md
  echo "|----------|-------------|" >> ${root_dir}/${hashalgo}.md
  for line in $(cat ${root_dir}/${hashalgo}.csv); do
    checksum=$(echo ${line} | cut -d";" -f1)
    filename=$(echo ${line} | cut -d";" -f2)
    echo "checksum [${checksum}]"
    if [[ "${uploaded_assets}" =~ "${checksum}" ]]; then
      echo "${hashalgo}: skipping ${checksum}"
    else
      githubrelease asset Slicer/SlicerTestingData upload ${hashalgo} ${root_dir}/${hashalgo}/${checksum}
    fi
    echo "| [$filename](https://github.com/Slicer/SlicerTestingData/releases/download/${hashalgo}/${checksum}) | ${checksum} |" >> ${root_dir}/${hashalgo}.md
  done
  echo

  #----
  echo "${hashalgo}: updating ${hashalgo}.csv and ${hashalgo}.md"
  githubrelease asset Slicer/SlicerTestingData delete ${hashalgo} "${hashalgo}.csv ${hashalgo}.md"
  githubrelease asset Slicer/SlicerTestingData upload ${hashalgo} ${root_dir}/${hashalgo}.csv ${root_dir}/${hashalgo}.md
  echo

  #----
  echo "${hashalgo}: updating release notes"
  githubrelease release Slicer/SlicerTestingData edit --body "$(cat ${root_dir}/${hashalgo}.md)" ${hashalgo}

done
