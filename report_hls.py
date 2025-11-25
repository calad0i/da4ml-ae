import argparse
import json
import os
import re
from math import ceil, log10
from pathlib import Path

from lxml import etree


def parse_csynth(xml_str: str) -> dict:
    xpaths = {
        'best_latency': '/profile/PerformanceEstimates/SummaryOfOverallLatency/Best-caseLatency/text()',
        'worst_latency': '/profile/PerformanceEstimates/SummaryOfOverallLatency/Worst-caseLatency/text()',
        'pipeline': '/profile/PerformanceEstimates/PipelineType/text()',
        'best_II': '/profile/PerformanceEstimates/SummaryOfOverallLatency/Interval-min/text()',
        'worst_II': '/profile/PerformanceEstimates/SummaryOfOverallLatency/Interval-max/text()',
        'BRAM18': '/profile/AreaEstimates/Resources/BRAM_18K/text()',
        'DSP': '/profile/AreaEstimates/Resources/DSP/text()',
        'FF': '/profile/AreaEstimates/Resources/FF/text()',
        'LUT': '/profile/AreaEstimates/Resources/LUT/text()',
        'URAM': '/profile/AreaEstimates/Resources/URAM/text()',
    }
    xml_str = re.sub(r'DSP48E?\d?', 'DSP', xml_str)
    r = {}
    xml = etree.fromstring(xml_str, None)
    for k, v in xpaths.items():
        try:
            x = xml.xpath(v)[0]
        except IndexError:
            print(k, v)
            raise
        r[k] = int(x) if x.isdigit() else x
    return r


def parse_export(xml_str: str) -> dict:
    xpaths = {
        'CLB': '/profile/AreaReport/Resources/CLB/text()',
        'BRAM18': '/profile/AreaReport/Resources/BRAM/text()',
        'DSP': '/profile/AreaReport/Resources/DSP/text()',
        'FF': '/profile/AreaReport/Resources/FF/text()',
        'LUT': '/profile/AreaReport/Resources/LUT/text()',
        'URAM': '/profile/AreaReport/Resources/URAM/text()',
        'target_clock_period': '/profile/TimingReport/TargetClockPeriod/text()',
        'actual_clock_period': '/profile/TimingReport/AchievedClockPeriod/text()',
        'avail_LUT': '/profile/AreaReport/AvailableResources/LUT/text()',
        'avail_DSP': '/profile/AreaReport/AvailableResources/DSP/text()',
        'avail_FF': '/profile/AreaReport/AvailableResources/FF/text()',
        'avail_BRAM18': '/profile/AreaReport/AvailableResources/BRAM/text()',
        'avail_URAM': '/profile/AreaReport/AvailableResources/URAM/text()',
    }
    xml_str = re.sub(r'DSP48E?\d?', 'DSP', xml_str)
    xml = etree.fromstring(xml_str, None)
    r = {}
    for k, v in xpaths.items():
        x = xml.xpath(v)[0]
        if k == 'target_clock_period' or k == 'actual_clock_period':
            r[k] = float(x) if x != 'NA' else float('nan')
        else:
            r[k] = int(x)
    return r


def summarize(csynth: dict, export: dict) -> dict:
    assert csynth['worst_latency'] == csynth.pop('best_latency')
    assert csynth['worst_II'] == csynth.pop('best_II')
    return {
        'Latency': csynth.pop('worst_latency'),
        'LUT': export['LUT'],
        'DSP': export['DSP'],
        'FF': export['FF'],
        'II': csynth.pop('worst_II'),
        'BRAM18': export['BRAM18'],
        'URAM': export['URAM'],
        'pipeline': csynth.pop('pipeline'),
        'target_clock_period': export['target_clock_period'],
        'actual_clock_period': export['actual_clock_period'],
        'avail_LUT': export['avail_LUT'],
        'avail_DSP': export['avail_DSP'],
        'avail_FF': export['avail_FF'],
        'avail_BRAM18': export['avail_BRAM18'],
        'avail_URAM': export['avail_URAM'],
        # 'synth_resource': csynth,
    }


def load_summary(path: Path) -> dict:
    prj_name = ''
    with open(path / 'project.tcl', 'r') as f:
        txt = f.read().split('set project_name ', 1)[1]
        prj_name = txt.splitlines()[0].strip().strip('"')

    csynth_xml_path = (
        path / f'{prj_name}_prj/solution1/syn/report/{prj_name}_csynth.xml'
    )

    for lang in ('vhdl', 'verilog'):
        for name in (f'{prj_name}_export.xml', 'export_impl.xml'):
            export_xml_path = (
                path / f'{prj_name}_prj/solution1/impl/report/{lang}/{name}'
            )
            if export_xml_path.exists():
                break
        else:
            continue
        break
    else:
        raise FileNotFoundError(f'No export.xml found in {path}')
    if not csynth_xml_path.exists():
        print(f'No csynth.xml found at {csynth_xml_path}')
        return {}

    with open(csynth_xml_path) as xml:
        xml_str = xml.read()
        csynth = parse_csynth(xml_str)
    with open(export_xml_path) as xml:
        xml_str = xml.read()
        export = parse_export(xml_str)

    summary = summarize(csynth, export)
    summary['Latency [ns]'] = summary['Latency'] * summary['actual_clock_period']
    summary['Fmax [MHz]'] = 1000.0 / summary['actual_clock_period']

    return summary


def parse_timing_summary(timing_summary: str):
    loc0 = timing_summary.find('Design Timing Summary')
    lines = timing_summary[loc0:].split('\n')[3:10]
    lines = [line for line in lines if line.strip() != '']

    assert set(lines[1]) == {' ', '-'}
    keys = [k.strip() for k in lines[0].split('  ') if k]
    vals = [int(v) if '.' not in v else float(v) for v in lines[2].split('  ') if v]
    assert len(keys) == len(vals)
    d = dict(zip(keys, vals))
    return d


def extra_info_from_fname(fname: str):
    d = {}
    parts = re.split(r'(?<!e)(?<!=)-(?!\d)', fname)
    for part in parts:
        if '=' not in part:
            continue
        k, v = part.split('=', 1)
        if '.' in v:
            try:
                v = float(v)
                d[k] = v
                continue
            except ValueError:
                pass
        else:
            try:
                v = int(v)
                d[k] = v
                continue
            except ValueError:
                pass
        d[k] = v
    return d


def pretty_print(arr: list[list]):
    n_cols = len(arr[0])
    terminal_width = os.get_terminal_size().columns
    default_width = [
        max(
            min(6, len(str(arr[i][j])))
            if isinstance(arr[i][j], float)
            else len(str(arr[i][j]))
            for i in range(len(arr))
        )
        for j in range(n_cols)
    ]
    if sum(default_width) + 2 * n_cols + 1 <= terminal_width:
        col_width = default_width
    else:
        th = max(8, (terminal_width - 2 * n_cols - 1) // n_cols)
        col_width = [min(w, th) for w in default_width]

    header = [
        '| '
        + ' | '.join(
            f'{str(arr[0][i]).ljust(col_width[i])[: col_width[i]]}'
            for i in range(n_cols)
        )
        + ' |',
        '|-' + '-|-'.join('-' * col_width[i] for i in range(n_cols)) + '-|',
    ]
    content = []
    for row in arr[1:]:
        _row = []
        for i, v in enumerate(row):
            w = col_width[i]
            if type(v) is float:
                n_int = ceil(log10(abs(v) + 1)) if v != 0 else 1 + (v < 0)
                v = round(v, 10 - n_int)
                if type(v) is int:
                    fmt = f'{{:>{w}d}}'
                    _v = fmt.format(v)
                else:
                    _v = str(v)
                    if len(_v) > w:
                        fmt = f'{{:.{w - n_int - 1}f}}'
                        _v = fmt.format(v).ljust(w)
                    else:
                        _v = _v.ljust(w)
            else:
                _v = str(v).ljust(w)[:w]
            _row.append(_v)
        content.append('| ' + ' | '.join(_row) + ' |')
    print('\n'.join(header + content))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Load hls4ml summaries')
    parser.add_argument(
        'paths',
        type=str,
        nargs='+',
        help='Paths to the directories containing HDL summaries',
    )
    parser.add_argument(
        '--output',
        '-o',
        type=str,
        default='stdout',
        help='Output file name for the summary',
    )
    parser.add_argument(
        '--extra', '-e', type=str, default='', help='Extra info to add to the summary'
    )
    parser.add_argument(
        '--sort-by',
        '-s',
        type=str,
        nargs='*',
        default=[],
    )
    parser.add_argument(
        '--columns',
        '-c',
        type=str,
        nargs='*',
        default=[],
    )

    args = parser.parse_args()

    vals = [load_summary(Path(p)) for p in args.paths]
    for path, val in zip(args.paths, vals):
        d = extra_info_from_fname(Path(path).name)
        for k, v in d.items():
            val.setdefault(k, v)

    if args.extra:
        with open(args.extra) as f:
            extra = json.load(f)
        dd = {a['epoch']: a for a in vals}
        d = {int(k.split('-', 1)[0].split('=', 1)[1]): v for k, v in extra.items()}
        for k, v in dd.items():
            assert k in d, f'No extra info for {k}'
            v.update(d[k])

    attrs = set()
    for v in vals:
        attrs.update(v.keys())
    attrs = sorted(attrs)
    arr: list[list] = [list(attrs)]
    for v in vals:
        arr.append([v.get(a, '') for a in attrs])

    if args.sort_by:
        sort_indices = [
            attrs.index(k[1:]) if k.startswith('_') else attrs.index(k)
            for k in args.sort_by
        ]
        signs = [-1 if k.startswith('_') else 1 for k in args.sort_by]

        arr = [arr[0]] + sorted(
            arr[1:],
            key=lambda x: tuple(
                s
                * (
                    (x[i] if x[i] >= 0 else -100 * x[i])
                    if isinstance(x[i], (float, int))
                    else -float('inf')
                )
                for i, s in zip(sort_indices, signs)
            ),
        )

    if args.columns:
        col_indices = [attrs.index(c) for c in args.columns]
        arr = [[col[i] for i in col_indices] for col in arr]

    if args.output == 'stdout':
        if not args.columns:
            mask = [not name.startswith('avail_') for name in arr[0]]
            arr = [[col for i, col in enumerate(row) if mask[i]] for row in arr]
        pretty_print(arr)
        exit(0)

    with open(args.output, 'w') as f:
        ext = Path(args.output).suffix
        if ext == '.json':
            json.dump(vals, f)
        elif ext in ['.tsv', '.csv']:
            sep = ',' if ext == '.csv' else '\t'
            op = (
                (lambda x: str(x) if ',' not in str(x) else f'"{str(x)}"')
                if ext == '.csv'
                else lambda x: str(x)
            )
            for row in arr:
                f.write(sep.join(map(op, row)) + '\n')  # type: ignore
        elif ext == '.md':
            f.write('| ' + ' | '.join(map(str, arr[0])) + ' |\n')
            f.write('|' + '|'.join(['---'] * len(arr[0])) + '|\n')
            for row in arr[1:]:
                f.write('| ' + ' | '.join(map(str, row)) + ' |\n')
        elif ext == '.html':
            f.write('<table>\n')
            f.write('  <tr>' + ''.join([f'<th>{a}</th>' for a in arr[0]]) + '</tr>\n')
            for row in arr[1:]:
                f.write('  <tr>' + ''.join([f'<td>{a}</td>' for a in row]) + '</tr>\n')
            f.write('</table>\n')
        else:
            raise ValueError(f'Unsupported output format: {ext}')
