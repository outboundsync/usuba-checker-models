#!/bin/bash
repo=$1; c=$2; id=$3; d=repos/$id
[ -d $d/.git ] && exit 0
git init -q $d && cd $d && git remote add origin $repo && \
 (timeout 120 git fetch -q --depth 1 origin $c 2>/dev/null && git checkout -q FETCH_HEAD) || (timeout 120 git fetch -q --depth 1 origin HEAD && git checkout -q FETCH_HEAD && echo "fallback-HEAD $id")
