from collections import defaultdict
import re
import sys


filename = sys.argv[1]

class Parser():
    sync_track = []
    resolution = 192
    new_parts = {}
    lines = []

    def get_on_beat(self, milliseconds):
        # return true if milliseconds are on beat
        return milliseconds % self.resolution == 0

    def notes_to_easy_single(self, notes):
        # 4 -> 0
        # 3 -> 1
        # No chords
        ret = []
        for note in notes[:1]:
            _, color, length = note.split(' ')
            if color == '4':
                color = '0'
            elif color == '3':
                color = '1'
            ret.append('N {} {}'.format(color, length))
        return ret

    def notes_to_easy_drums(self, notes):
        # No 0
        # No chords
        for note in notes:
            _, color, length = note.split(' ')
            if color == '0':
                continue
            return ['N {} {}'.format(color, length)]

        return []

    def parse_expert_part(self, part, part_lines):
        print("parsing expret track", part)
        easy_lines = []
        notes_by_ms = defaultdict(list)
        for line in part_lines:
            if '=' not in line:
                continue
            ms, value = [_line__part.strip() for _line__part in line.split('=')]
            ms = int(ms)
            notes_by_ms[ms].append(value)
        
        for ms, lines in notes_by_ms.items():
            if self.get_on_beat(ms):
                if 'Drums' not in part:
                    for easy_note in self.notes_to_easy_single(lines):
                        easy_lines.append('{} = {}'.format(ms, easy_note))
                else:
                    for easy_note in self.notes_to_easy_drums(lines):
                        easy_lines.append('{} = {}'.format(ms, easy_note))
        
        easy_part = part.replace('Expert', 'Easy')
        self.new_parts[easy_part] = ['{'] + easy_lines + ['}']
        print('\n'.join(easy_lines))


    def parse_sync_track_part(self, part_lines):
        sync_track = []
        for line in part_lines:
            if '=' not in line:
                continue
            key, value = [_line__part.strip() for _line__part in line.split('=')]
            if not value.startswith('B '):
                continue
            key = key.strip()
            value = int(value.replace('B ', '').strip())
            sync_track.append((key, value))
        self.sync_track = sync_track
        print("sync track: ", sync_track)

    def parse_song_part(self, part_lines):
        print("parsing song part")
        for line in part_lines:
            if '=' not in line:
                continue
            key, value = [_line__part.strip() for _line__part in line.split('=')]
            if key == 'Resolution':
                self.resolution = int(value)


    def parse_file(self, lines):
        part = None
        part_lines = []

        for line in lines:
            self.lines.append(line)
            if re.match(r'^\[\w*\]$', line):
                part = line
                continue
            if line == '}':
                if part:
                    if '[Expert' in part:
                        self.parse_expert_part(part, part_lines)
                    if part == '[SyncTrack]':
                        self.parse_sync_track_part(part_lines)
                    if part == '[Song]':
                        self.parse_song_part(part_lines)
                    part = None
                    part_lines = []

            if part:
                part_lines.append(line)

    def write_file(self, new_filename):
        new_lines = []

        for line in self.lines:
            part = None
            if re.match(r'^\[\w*\]$', line):
                part = line
                new_lines.append(line)
                continue
            if line == '}':
                if part:
                    part = None
            
            if part:
                if part not in self.new_parts:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        
        for part, lines in self.new_parts.items():
            new_lines.append(part)
            new_lines.extend(lines)
        
        with open(new_filename, 'w') as f:
            f.write('\n'.join(new_lines))

with open(filename, 'r') as f:
    lines = [line.strip() for line in f.readlines()]

parser = Parser()
parser.parse_file(lines)
parser.write_file('easy_' + filename)
