""" Sample sanity parser """

import json

import proto_path


def builder():
    """ Construction code, for posterity. Do not use. """
    print('Starting parse')
    ws = get_ws_session()

    with open('dump.json', 'r') as f:
        raw = json.load(f)

    print('loaded', len(raw), 'reports')

    working_reports = []

    for report in raw:
        try:
            instance = ws.instance_get(report['programInstanceId'])
            path = ws.path_get_protobuf(instance['pathId'])

            with open(f"paths/{instance['pathId']}", 'w') as f:
                f.write(path)

            report['pathId'] = instance['pathId']
            working_reports.append(report)

        except Exception:
            # print('No proto path', e)
            continue

    print('Total reports with associated paths: ', len(working_reports))

    with open('dump_matching.json', 'w+') as f:
        json.dump(working_reports, f)


def main():
    # Load the reports that have already been pulled aside as having valid paths
    with open('dump_matching.json', 'r') as f:
        reports = json.load(f)

    # Load a proto path, once for each matching path in the reports dump
    for report in reports:
        with open(f'paths/{report["pathId"]}', 'r') as f:
            report['path'] = proto_path.Path(f.read())

    print(f'Loaded {len(reports)} reports and attached paths.')


if __name__ == '__main__':
    main()
    builder()



