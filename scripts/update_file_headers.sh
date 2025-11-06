#!/bin/bash

cd $(dirname $0)
licenseheaders -t bsd-3.tmpl --dir ../src --ext .py
