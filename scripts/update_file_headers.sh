#!/bin/bash

cd $(dirname $0)
for folder in ../myna ../tests;
do
    echo $(realpath $folder)
    licenseheaders -t bsd-3.tmpl -y 2024 --dir $folder --ext .py
done
