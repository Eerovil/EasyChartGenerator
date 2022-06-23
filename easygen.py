#
# Clone Hero difficulties generator script
# 
# Usage: python3 easygen.py mysong.chart <multiplier>
# Will generate a new file called easy_mysong.chart in the current directory.
#
# If your song has very slow or fast BPM, pass a multiplier after the filename to make the charts easier/harder.
# 
#
# Change Log:
# 23-06-2022 @ 05:00 GMT: Screenshots: https://imgur.com/a/pBLCUqS
# * Fixed songs with star power
# * Fixed songs with events
# * Fixed songs with existing parts
# * Don't always replace exisiting parts (set FORCE_REPLACE_PARTS if you need this)
#

from collections import defaultdict
import re
import sys

FORCE_REPLACE_PARTS = True

filename = sys.argv[1]
global_beat_multiplier = 1
if len(sys.argv) > 2:
    global_beat_multiplier = float(sys.argv[2])

class Parser():
    sync_track = []
    resolution = 192
    new_parts = {}
    lines = []

    def get_bpm_for_ms(self, ms):
        ret_ms = None
        ret_bpm = None
        line_bpm = None
        for line in self.sync_track:
            if 'B ' not in line[1] and 'TS ' not in line[1]:
                continue
            line_ms = int(line[0])
            if 'B ' in line[1]:
                line_bpm = int(line[1].replace('B ', '').strip())
            if ret_bpm is None:
                ret_bpm = line_bpm
                ret_ms = line_ms
            if line_ms <= ms:
                ret_bpm = line_bpm
                ret_ms = line_ms
            if line_ms > ms:
                break
        return ret_bpm, ret_ms

    def get_on_beat(self, milliseconds, beat_multiplier=1):
        # return true if milliseconds are on beat
        bpm, bpm_ms = self.get_bpm_for_ms(milliseconds)
        milliseconds -= bpm_ms
        return milliseconds % int(self.resolution * global_beat_multiplier * beat_multiplier) == 0

    def notes_to_diff_single(self, diff, ms, notes, ms_delta_around=0):
        ret = []
        if diff == 'easy':
            # 4 -> 0
            # 3 -> 1
            # No chords
            if (ms_delta_around < self.resolution * global_beat_multiplier * 2) and not self.get_on_beat(ms, beat_multiplier=2):
                return ret
            for note in notes[:1]:
                _, color, length = note.split(' ')
                if color == '4':
                    color = '0'
                elif color == '3':
                    color = '1'
                ret.append('N {} {}'.format(color, length))
            return ret

        if diff == 'medium':
            # 4 -> 1
            # Max 2 lenngth chords
            if (ms_delta_around < self.resolution * global_beat_multiplier) and not self.get_on_beat(ms):
                return ret
            for note in notes[:2]:
                _, color, length = note.split(' ')
                if color == '4':
                    color = '0'
                ret.append('N {} {}'.format(color, length))
            return ret

        if diff == 'hard':
            if (ms_delta_around < self.resolution * global_beat_multiplier * 0.5) and not self.get_on_beat(ms, beat_multiplier=0.5):
                return []
            return notes

    def notes_to_diff_drums(self, diff, ms, notes, ms_delta_around=0):
        ret = []
        if diff == 'easy':
            # No chords
            if (ms_delta_around < self.resolution * global_beat_multiplier * 2) and not self.get_on_beat(ms, beat_multiplier=2):
                return []
            for note in notes:
                _, color, length = note.split(' ')
                return ['N {} {}'.format(color, length)]
            return ret

        if diff == 'medium':
            # 2 max chords
            # 0 only alone
            ret = []
            if (ms_delta_around < self.resolution * global_beat_multiplier) and not self.get_on_beat(ms):
                return []
            for note in notes[:2]:
                _, color, length = note.split(' ')
                if len(notes) > 1 and color == '0':
                    continue
                ret.append('N {} {}'.format(color, length))
            return ret

        if diff == 'hard':
            if (ms_delta_around < self.resolution * global_beat_multiplier) and not self.get_on_beat(ms):
                return []
            return notes

        return ret

    def parse_expert_part(self, part, part_lines):
        print("parsing expert track", part)
        difficulty_lines = defaultdict(list)
        notes_by_ms = defaultdict(list)
        for line in part_lines:
            if '=' not in line:
                continue
            ms, value = [_line__part.strip() for _line__part in line.split('=')]
            ms = int(ms)
            notes_by_ms[ms].append(value)
        
        ms_list = list(notes_by_ms.keys())
        next_ms = 0
        prev_ms = 0
        index = 0
        for ms, lines in notes_by_ms.items():
            notes = [_line for _line in lines if _line.startswith('N ')]
            if len(notes) > 0:
                if index < len(notes_by_ms) - 1:
                    next_ms = ms_list[index + 1]
                if index > 0:
                    prev_ms = ms_list[index - 1]
            for diff in ['easy', 'medium', 'hard']:
                for non_note_line in lines:
                    if non_note_line in notes:
                        continue
                    difficulty_lines[diff].append('{} = {}'.format(ms, non_note_line))
                if 'Drums' not in part:
                    for easy_note in self.notes_to_diff_single(diff, ms, notes, ms_delta_around=min(ms - prev_ms, next_ms - ms)):
                        difficulty_lines[diff].append('{} = {}'.format(ms, easy_note))
                else:
                    for easy_note in self.notes_to_diff_drums(diff, ms, notes, ms_delta_around=min(ms - prev_ms, next_ms - ms)):
                        difficulty_lines[diff].append('{} = {}'.format(ms, easy_note))
            index += 1
        
        for diff in ['easy', 'medium', 'hard']:
            easy_part = part.replace('Expert', diff.capitalize())
            print("Got new part ", easy_part)
            self.new_parts[easy_part] = ['{'] + difficulty_lines[diff] + ['}']


    def parse_sync_track_part(self, part_lines):
        sync_track = []
        for line in part_lines:
            if '=' not in line:
                continue
            key, value = [_line__part.strip() for _line__part in line.split('=')]
            key = key.strip()
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

        replace = False

        parts = defaultdict(list)
        for line in self.lines:
            if re.match(r'^.*\[\w*\].*$', line):
                part = line.strip()
                parts[part].append(line)
                continue

            if line == '}':
                if part:
                    parts[part].append(line)
                    part = None
                    continue

            if part:
                parts[part].append(line)

        for partname, lines in parts.items():
            if partname in self.new_parts.keys():
                if FORCE_REPLACE_PARTS:
                    print("Replacing existing part ", partname)
                    continue
                else:
                    print("Part ", partname, " already exists, skipping")
            new_lines.extend(lines)

        for partname, lines in self.new_parts.items():
            if not FORCE_REPLACE_PARTS:
                if partname in parts.keys():
                    continue
            new_lines.append(partname)
            new_lines.extend(lines)
        
        with open(new_filename, 'w') as f:
            f.write('\n'.join(new_lines))

with open(filename, 'r') as f:
    lines = [line.strip() for line in f.readlines()]

parser = Parser()
parser.parse_file(lines)
parser.write_file('easy_' + filename)
