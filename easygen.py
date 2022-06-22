import re


filename = sys.argv[1]

class Parser():
    def get_on_beat(self)


    def parse_expert_part(self, part_lines):
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
        self.sync_track = sync_track


    def parse_file(lines):
        part = None
        part_lines = []
        sync_track = []
        for line in lines:
            if re.match(r'^[\w*]$', line):
                part = line
                continue
            if line == '}':
                if part:
                    if '[Expert' in part:
                        parse_expert_part(part_lines, sync_track=sync_track)
                    if part == '[SyncTrack]':
                        sync_track = parse_sync_track_part(part_lines)
                    part = None
                    part_lines = []

            if part:
                part_lines.append(line)


with open(filename, 'r') as f:
    lines = f.readlines()

parser = Parser()
parser.parse_file(lines)
