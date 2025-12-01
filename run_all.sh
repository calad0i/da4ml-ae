# ==============================================
# Global configurations
# ==============================================

export WORKING_DIR_RANDMAT=prjs/rand_mat # example path, edit as needed
export N_PROC=4 # Number of parallel instances for synthesis, set according to your system capabilities

# ==============================================
# Run all experiments
# ==============================================

#---------------------------------
# Random Matrices (Tables 3 and 4)
#---------------------------------

# Convert the random matrices, enforcing a latency of one clock cycle for measuring combinational delay
./convert_rand_mat.sh $WORKING_DIR_RANDMAT

# Run HLS synthesis. If you do not have gnu_parallel installed, you can run the commands one by one inside each directory.
ls -d $WORKING_DIR_RANDMAT/* | parallel --bar -j $N_PROC 'cd {} && singularity exec /data/containers/vivado-2023.2.sif vitis-run --mode hls --tcl build_prj.tcl > synth.log'

# Print reports for tables 3 and 4
echo Table 3:
python report_hls.py $WORKING_DIR_RANDMAT/*bw=8* -s N dc -c dc N LUT DSP FF 'Latency [ns]'
echo Table 4:
python report_hls.py $WORKING_DIR_RANDMAT/*bw=4* -s N dc -c dc N LUT DSP FF 'Latency [ns]'

#-------------------------------------
# JSC Models (Tables 5, 6, 10, and 11)
#-------------------------------------

export WORKING_DIR_JSC_OPENML=prjs/jsc_openml

# Convert with targets of 200MHz and 1GHz
./convert.sh jsc/openml $WORKING_DIR_JSC_OPENML 5
./convert.sh jsc/openml $WORKING_DIR_JSC_OPENML 1

# Run HLS synthesis 
ls -d $WORKING_DIR_JSC_OPENML/*/* | parallel --bar -j $N_PROC 'cd {} && singularity exec /data/containers/vivado-2023.2.sif vitis-run --mode hls --tcl build_prj.tcl > synth.log'

# Print reports for tables 5 and 6
echo Table 5
python report_hls.py $WORKING_DIR_JSC_OPENML/period=5/* -s _test_acc -c use_da test_acc Latency 'Latency [ns]' LUT DSP FF 'Fmax [MHz]'
echo Table 6
python report_hls.py $WORKING_DIR_JSC_OPENML/period=1/* -s _test_acc -c use_da test_acc Latency 'Latency [ns]' LUT DSP FF 'Fmax [MHz]'

ls -d $WORKING_DIR_JSC_OPENML/rtl-period=*/* | parallel --bar -j $N_PROC 'cd {} && vivado -mode batch -source build_vivado_prj.tcl > synth.log'

# Print reports for RTL models in tables 10 and 11
echo Table 10-RTL:
da4ml report $WORKING_DIR_JSC_OPENML/rtl-period=5/* -c test_acc latency 'latency(ns)' LUT DSP FF 'Fmax(MHz)'
echo Table 11-RTL:
da4ml report $WORKING_DIR_JSC_OPENML/rtl-period=1/* -c test_acc latency 'latency(ns)' LUT DSP FF 'Fmax(MHz)'

#---------------------------------
# MLP-Mixer (Tables 9 and 12)
#---------------------------------

export WORKING_DIR_MLPM=prjs/mlp-mixer

# Convert with target frequency of 200MHz
./convert.sh mlp-mixer $WORKING_DIR_MLPM 5

# Run HLS synthesis for table 9
ls -d $WORKING_DIR_MLPM/period=5/* | parallel --bar -j $N_PROC 'cd {} && singularity exec /data/containers/vivado-2023.2.sif vitis-run --mode hls --tcl build_prj.tcl > synth.log'

# Print reports for table 9
echo Table 9
python report_hls.py $WORKING_DIR_MLPM/period=5/* -s _test_acc -c use_da test_acc Latency 'Latency [ns]' LUT DSP FF 'Fmax [MHz]'


ls -d $WORKING_DIR_MLPM/rtl-period=5/* | parallel --bar -j $N_PROC 'cd {} && vivado -mode batch -source build_vivado_prj.tcl > synth.log'

# Print reports for RTL models in table 12
echo Table 12-RTL
da4ml report $WORKING_DIR_MLPM/rtl-period=5/* -c test_acc latency 'latency(ns)' LUT DSP FF 'Fmax(MHz)'


#---------------------------------
# JSC CERNBox (from Table 13)
#---------------------------------

export WORKING_DIR_CERNBOX=prjs/jsc_cernbox

# Convert with target frequency of 1GHz
./convert.sh jsc/cernbox $WORKING_DIR_CERNBOX 1

# Run Vivado OOC P&R
ls -d $WORKING_DIR_CERNBOX/rtl-period=1/* | parallel --bar -j $N_PROC 'cd {} && vivado -mode batch -source build_vivado_prj.tcl > synth.log'

# Print reports for RTL models in table 13
echo CERNBox Table 13
da4ml report $WORKING_DIR_CERNBOX/rtl-period=1/* -c test_acc latency 'latency(ns)' LUT DSP FF 'Fmax(MHz)'
