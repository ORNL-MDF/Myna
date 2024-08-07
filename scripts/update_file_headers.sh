#!/bin/bash

cd $(dirname $0)
cd ..
for folder in myna tests;
do
    filelist=$()
    licenseheaders -t $(realpath ../scripts/bsd-3.tmpl) -y 2024 --ext *.py
    cd ..
done
