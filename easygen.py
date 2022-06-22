import re


filename = sys.argv[1]

class Parser():
    sync_track = []

    def get_bpm(self, milliseconds):
        # Get bpm current
        bpm = None
        bpm_start = None
        for line in self.sync_track:
            if bpm = None:
                bpm = line[1]
                bpm_start = line[0]
            if line[0] < milliseconds:
                bpm = line[1]
                bpm_start = line[0]
            if line[0] > milliseconds:
                break
        return bpm, bpm_start

    def get_on_beat(self, milliseconds):
        # return true if milliseconds are on beat
        bpm, bpm_start = self.get_bpm(milliseconds)
        milliseconds_per_beat = 60000 / bpm
        milliseconds -= bpm_start
        return milliseconds % milliseconds_per_beat == 0


    def parse_expert_part(self, part_lines):
        for line in part_lines:
            ms, value = [_line__part.strip() for _line__part in line.split(' = ')]
            ms = int(ms)
            if self.get_on_beat(ms)
            
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
