import re


filename = sys.argv[1]

class Parser():
    sync_track = []

    def get_bpm(self, milliseconds)
        # Get bpm current
        latest = None
        for line in self.sync_track:
            if latest = None:
                latest = line[1]
            if line[0] 

    def get_on_beat(self, milliseconds):
        # return true if milliseconds are on beat


    def parse_expert_part(self, part_lines):
        pass


    def parse_sync_track_part(self, part_lines):
        sync_track = []
        for line in part_lines:
            if '=' not in line:
                continue
            key, value = line.split('=')
            if not value.startswith('B '):
                continue
            key = key.strip()
            value = int(value.replace('B ', '').strip())
            sync_track.append((key, value))
        self.sync_track = sync_track


    def parse_file(self, lines):
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
                        self.parse_expert_part(part_lines)
                    if part == '[SyncTrack]':
                        self.parse_sync_track_part(part_lines)
                    part = None
                    part_lines = []

            if part:
                part_lines.append(line)


with open(filename, 'r') as f:
    lines = f.readlines()

parser = Parser()
parser.parse_file(lines)
