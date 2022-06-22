import re


filename = sys.argv[1]


def parse_expert_part(part_lines):
    pass


def parse_sync_track_part(part_lines):
    sync_track = []
    for line in part_lines:
        if '=' not in line:
            continue
        key, value = line.split('=')
        if not value.startswith('B '):
            continue
        key = key.strip()
        value = value.replace('B ', '').strip()
        sync_track.append((key, value))


def parse_file(lines):
    part = None
    part_lines = []
    for line in lines:
        if re.match(r'^[\w*]$', line):
            part = line
            continue
        if line == '}':
            if part:
                if '[Expert' in part:
                    parse_expert_part(part_lines)
                if part == '[SyncTrack]':
                    parse_sync_track_part(part_lines)
                part = None
                part_lines = []

        if part:
            part_lines.append(line)


with open(filename, 'r') as f:
    lines = f.readlines()
    parse_file(lines)
