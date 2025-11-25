#!/bin/bash

SRC="$1"
PATH_OUT="$2"
PERIOD="$3"
NJOBS="$4"

if [ -z "$NJOBS" ]; then
    NJOBS=4
fi

mkdir -p $PATH_OUT

if [ ! -d $SRC ]; then
    echo "Source path $SRC is not a directory"
    exit 1
fi

function cmd_print(){
    for f in $(ls "$SRC"); do
        echo python convert_hls.py "$SRC/$f" --clock-period $PERIOD -o $PATH_OUT/period=$PERIOD/use_da=1-$(basename ${f%.*}) --use-da4ml --delay-constraint 2
        echo python convert_hls.py "$SRC/$f" --clock-period $PERIOD -o $PATH_OUT/period=$PERIOD/use_da=0-$(basename ${f%.*})
        echo KERAS_BACKEND=jax JAX_PLATFORM_NAME=cpu da4ml convert "$SRC/$f" --clock-period $PERIOD $PATH_OUT/rtl-period=$PERIOD/$(basename ${f%.*}) --unc 0 --latency-cutoff $PERIOD --verbose 0 -dc 2 -n 0
    done
}

if [ $(which parallel) == "" ]; then
    for cmd in $(cmd_print); do
        eval $cmd
    done
    exit 0
else
    cmd_print | parallel -j $NJOBS --bar {}
fi