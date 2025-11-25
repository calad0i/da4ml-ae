import argparse
import os
import re

os.environ['KERAS_BACKEND'] = 'jax'
os.environ['JAX_PLATFORM_NAME'] = 'cpu'


import hgq  # noqa: F401
import hls4ml
import keras


def convert(
    model_path,
    use_da4ml: bool,
    delay_constraint: int,
    output_dir: str,
    clock_period: float,
    force_latency: int,
):
    model: keras.Model = keras.models.load_model(model_path, compile=False)  # type: ignore

    os.environ['DA_HARD_DC'] = str(delay_constraint)
    strategy = 'distributed_arithmetic' if use_da4ml else 'Latency'
    hls_config = {
        'Model': {
            'Precision': 'fixed<-1,0>',  # The default invalid precision will never be used
            'ReuseFactor': 1,
            'Strategy': strategy,
        }
    }
    model_hls = hls4ml.converters.convert_from_keras_model(
        model,
        hls_config=hls_config,
        output_dir=output_dir,
        clock_uncertainty=0,
        clock_period=clock_period,
        part='xcvu13p-flga2577-2-e',
        backend='vitis',
    )
    model_hls.write()

    # print(sum(g.attributes.get('da_kernel_cost', 0) for g in model_hls.graph.values()))

    # Patches

    # Run OOC with vivado default strategy
    with open(os.path.join(output_dir, 'build_opt.tcl'), 'w') as f:
        f.write("""array set opt {
    reset      0
    csim       0
    synth      1
    cosim      0
    validation 0
    export     1
    vsynth     0
    fifo_opt   0
}
""")
    with open(os.path.join(output_dir, 'build_prj.tcl'), 'r') as f:
        build_prj = f.read()
    with open(os.path.join(output_dir, 'build_prj.tcl'), 'w') as f:
        f.write(
            build_prj.replace(
                'export_design -format', 'export_design -flow impl -rtl verilog -format'
            )
        )

    # Use inline recursive; better perf for II=1 designs
    with open(os.path.join(output_dir, 'firmware/myproject.cpp'), 'r') as f:
        top_fn = f.read()

    pragma = '#pragma HLS PIPELINE II=1\n    #pragma HLS INLINE recursive\n'
    if force_latency > 0:
        pragma += f'    #pragma HLS LATENCY min={force_latency} max={force_latency}\n'

    with open(os.path.join(output_dir, 'firmware/myproject.cpp'), 'w') as f:
        f.write(
            re.sub(
                r'#pragma HLS (?:PIPELINE|DATAFLOW)\s*\n',
                pragma,
                top_fn,
            )
        )

    if not use_da4ml and force_latency > 0:
        # Patch for Latency pragma to be enforced correctly...
        with open(
            os.path.join(output_dir, 'firmware/nnet_utils/nnet_dense_latency.h'), 'r'
        ) as f:
            dense_latency = f.read()
        dense_latency = dense_latency.replace(
            'data_T cache;', '#pragma HLS INLINE\n    data_T cache;'
        )
        with open(
            os.path.join(output_dir, 'firmware/nnet_utils/nnet_dense_latency.h'), 'w'
        ) as f:
            f.write(dense_latency)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('model_path', type=str, help='Path to Keras model file')
    parser.add_argument(
        '--use-da4ml', '-da', action='store_true', help='Use DA4ML backend'
    )
    parser.add_argument(
        '--delay-constraint',
        '-dc',
        type=int,
        default=2,
        help='Decimal point position for fixed-point representation',
    )
    parser.add_argument(
        '--output_dir',
        '-o',
        type=str,
        default='hls4ml_output',
        help='Output directory for HLS4ML project',
    )
    parser.add_argument(
        '--clock-period',
        '-p',
        type=float,
        default=5.0,
        help='Clock period for HLS synthesis (in ns)',
    )
    parser.add_argument(
        '--force-latency',
        type=int,
        default=0,
        help='Force global pipeline latency to this value',
    )

    args = parser.parse_args()

    convert(
        args.model_path,
        args.use_da4ml,
        args.delay_constraint,
        args.output_dir,
        args.clock_period,
        args.force_latency,
    )
