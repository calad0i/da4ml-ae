#!/bin/bash

PATH_OUT="$1"
mkdir -p $PATH_OUT

periods=( 1.0 1.25 1.75 2.0 )
Ns=( 8 16 32 64 )

function cmd_print(){
    for i in "${!Ns[@]}"; do
        N=${Ns[$i]}
        period=${periods[$i]}
        for bw in 4 8; do
            echo python convert_hls.py rand_mat/models/N=$N-bw=$bw.keras --clock-period $period --force-latency 1 -o $PATH_OUT/N=$N-bw=$bw-dc=-1 --use-da4ml --delay-constraint -1
            echo python convert_hls.py rand_mat/models/N=$N-bw=$bw.keras --clock-period $period --force-latency 1 -o $PATH_OUT/N=$N-bw=$bw-dc=2  --use-da4ml --delay-constraint 2
            echo python convert_hls.py rand_mat/models/N=$N-bw=$bw.keras --clock-period $period --force-latency 1 -o $PATH_OUT/N=$N-bw=$bw-dc=0  --use-da4ml --delay-constraint 0
            echo python convert_hls.py rand_mat/models/N=$N-bw=$bw.keras --clock-period $period --force-latency 1 -o $PATH_OUT/N=$N-bw=$bw-hls4ml
        done
    done
}

if [ $(which parallel) == "" ]; then
    for cmd in $(cmd_print); do
        eval $cmd
    done
    exit 0
else
    cmd_print | parallel -j 8 --bar {}
fi