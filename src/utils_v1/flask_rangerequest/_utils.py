from flask import abort


def parse_range_header(range_header: str, target_size: int) -> list:
    end_index = target_size - 1
    if range_header is None:
        return [(0, end_index)]

    bytes_ = 'bytes='
    if not range_header.startswith(bytes_):
        abort(416)

    ranges = []
    for range_ in range_header[len(bytes_):].split(','):
        split = range_.split('-')
        if len(split) == 1:
            try:
                start = int(split[0])
                end = end_index
            except ValueError:
                abort(416)
        elif len(split) == 2:
            start, end = split[0], split[1]
            if not start:
                # parse ranges of the form "bytes=-100" (i.e., last 100 bytes)
                end = end_index
                try:
                    start = end - int(split[1]) + 1
                except ValueError:
                    abort(416)
            else:
                # parse ranges of the form "bytes=100-200"
                try:
                    start = int(start)
                    if not end:
                        end = target_size
                    else:
                        end = int(end)
                except ValueError:
                    abort(416)

                if end < start:
                    abort(416)

                end = min(end, end_index)
        else:
            abort(416)

        ranges.append((start, end))

    # merge the ranges
    merged = []
    ranges = sorted(ranges, key=lambda x: x[0])
    for range_ in ranges:
        # initial case
        if not merged:
            merged.append(range_)
        else:
            # merge ranges that are adjacent or overlapping
            if range_[0] <= merged[-1][1] + 1:
                merged[-1] = (merged[-1][0], max(range_[1], merged[-1][1]))
            else:
                merged.append(range_)

    return merged
