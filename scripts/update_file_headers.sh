#!/bin/bash

cd $(dirname $0)
cd ../myna
licenseheaders -t ../scripts/bsd-3.tmpl -y 2024 -x *.sh
