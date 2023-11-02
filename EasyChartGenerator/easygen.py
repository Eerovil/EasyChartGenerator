
from collections import defaultdict
import re
import os
import argparse
import logging
logging.basicConfig(
    format="[%(levelname)s] %(message)s",
)


logger = logging.getLogger("easygen")


def parse_args(argument_parser_class=argparse.ArgumentParser):
    # Positional arg: filename
    if argument_parser_class is argparse.ArgumentParser:
        parser = argument_parser_class()
        parser.add_argument('filename', help='Filename of the file to parse')
    else:
        # Assumed GooeyParser
        parser = argument_parser_class(description="Choose Either 'filename' or 'directory' (for batch parsing)")
        parser.add_argument('--filename', help='Filename of the file to parse', widget="FileChooser")
        parser.add_argument('--directory', help='Filename of the directory to parse', widget="DirChooser")

    parser.add_argument('--batch', help='Read all files in the given path', action="store_true")
    parser.add_argument('--in_place', help='Modify files in place', action="store_true")

    parser.add_argument('--easy_bpm_cutoff', help='Bpm under this will have double the notes', default=120, type=int)
    parser.add_argument('--hard_bpm_cutoff', help='Bpm over this will have half the notes', default=200, type=int)
    parser.add_argument(
        '--custom_note_multiplier',
        help='Give 2 to make charts easier. Give 0.5 to make charts harder. NOTE: This is in addition to bmp_cutoffs',
        default=1,
        type=int
    )

    parser.add_argument('--easy', help='If this is given, only generate Easy difficulty', action="store_true")
    parser.add_argument('--medium', help='If this is given, only generate Medium difficulty', action="store_true")
    parser.add_argument('--hard', help='If this is given, only generate Hard difficulty', action="store_true")

    # 12600 - 12480 = 120
    # Double kick is note 32
    parser.add_argument(
        '--doublekick', help='Give ms value to automatically mark double kick on expert drums',
        action="store_true"
    )

    parser.add_argument('--force', help='If this is given, replace existing parts', action="store_true")

    parser.add_argument('-v', '--verbose', help='Verbose logs', action="store_true")
    return parser.parse_args()


class Parser():

    def __init__(self, options):
        self.sync_track = []
        self.resolution = 192
        self.new_parts = {}
        self.lines = []

        self.force_replace_parts = bool(options.force)
        self.easy_bpm_cutoff = options.easy_bpm_cutoff
        self.hard_bpm_cutoff = options.hard_bpm_cutoff
        self.custom_note_multiplier = options.custom_note_multiplier
        if options.easy or options.medium or options.hard:
            self.parts_to_generate = []
            if options.easy:
                self.parts_to_generate.append('easy')
            if options.medium:
                self.parts_to_generate.append('medium')
            if options.hard:
                self.parts_to_generate.append('hard')
        else:
            self.parts_to_generate = ['easy', 'medium', 'hard']

    def log_extra_bpm_multiplier(self, multiplier, bpm):
        # do this log only once per Parse instance
        if getattr(self, '_log_extra_bpm_multiplier_run', False):
            return
        logger.info("using extra note multiplier %s (bpm %s)", multiplier, bpm)
        self._log_extra_bpm_multiplier_run = True

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
        return (ret_bpm or 0) / 1000, ret_ms

    def ms_to_real_time_diff(self, ms, prev_ms):
        # Convert ms values to real time diff
        # To make them comparable in songs that have different bpm
        # parts
        bpm, bpm_ms = self.get_bpm_for_ms(prev_ms)
        if not bpm:
            return 99999
        ms_diff = ms - prev_ms
        beats = ms_diff / (self.resolution)
        # beats tells us how many beats the diff is
        # bpm = beats/minute
        # minutes = beats/bpm
        minutes = beats / bpm
        return minutes * 60000

    def get_on_beat(self, milliseconds, beat_multiplier=1, ms_delta_around=None):
        # return true if milliseconds are on beat
        bpm, bpm_ms = self.get_bpm_for_ms(milliseconds)
        extra_multiplier = 1
        if int(bpm) < self.easy_bpm_cutoff:
            extra_multiplier = 0.5
        if int(bpm) > self.hard_bpm_cutoff:
            extra_multiplier = 2
        if extra_multiplier != 1:
            self.log_extra_bpm_multiplier(extra_multiplier, bpm)
        milliseconds -= (bpm_ms or 0)
        if ms_delta_around is not None:
            if ms_delta_around > (self.resolution * self.custom_note_multiplier * extra_multiplier * beat_multiplier):
                return True

        return milliseconds % int(self.resolution * self.custom_note_multiplier * extra_multiplier * beat_multiplier) == 0

    def notes_to_diff_single(self, diff, ms, notes, ms_delta_around=0):
        ret = []
        if diff == 'easy':
            # 7 -> 0
            # 4 -> 0
            # 3 -> 1
            # No chords
            if not self.get_on_beat(ms, beat_multiplier=2, ms_delta_around=ms_delta_around):
                return ret
            for note in notes[:1]:
                _, color, length = note.split(' ')
                if color == '4':
                    color = '0'
                elif color == '3':
                    color = '1'
                elif color == '7':
                    color = '0'
                ret.append('N {} {}'.format(color, length))
            return ret

        if diff == 'medium':
            # 7 -> 0
            # 4 -> 1
            # Max 2 lenngth chords
            if not self.get_on_beat(ms, beat_multiplier=2, ms_delta_around=ms_delta_around):
                return ret
            for note in notes[:2]:
                _, color, length = note.split(' ')
                if color == '4':
                    color = '0'
                elif color == '7':
                    color = '0'
                ret.append('N {} {}'.format(color, length))
            return ret

        if diff == 'hard':
            # 7 -> 0
            if not self.get_on_beat(ms, beat_multiplier=0.5, ms_delta_around=ms_delta_around):
                return []
            return notes

    def notes_to_diff_drums(self, diff, ms, notes, ms_delta_around=0):
        ret = []
        off_beat = self.get_on_beat(ms, beat_multiplier=2, ms_delta_around=ms_delta_around)
        on_beat = self.get_on_beat(ms, beat_multiplier=4, ms_delta_around=ms_delta_around)
        if diff == 'easy':
            # No chords
            if not on_beat and not off_beat:
                return []

            if on_beat:
                # Allow bass or a single note
                for note in notes:
                    _, color, length = note.split(' ')
                    if color == '0':
                        ret.append('N {} {}'.format(color, length))
                        break
                else:
                    # No bass, allow single note
                    for note in notes:
                        _, color, length = note.split(' ')
                        ret.append('N {} {}'.format(color, length))
                        break
            elif off_beat:
                for note in notes:
                    _, color, length = note.split(' ')
                    if color == '0':
                        continue
                    ret.append('N {} {}'.format(color, length))
                    break

            return ret

        if diff == 'medium':
            if not on_beat and not off_beat:
                return []

            # 2 max chords
            # 0 only alone
            ret = []

            if on_beat:
                # Allow bass or a single note
                for note in notes:
                    _, color, length = note.split(' ')
                    if color == '0':
                        ret.append('N {} {}'.format(color, length))
                        break
                else:
                    # No bass, allow single note
                    for note in notes:
                        _, color, length = note.split(' ')
                        ret.append('N {} {}'.format(color, length))
                        break
            elif off_beat:
                # Allow 1-2 notes or bass
                _found_notes = 0
                for note in notes[:2]:
                    _, color, length = note.split(' ')
                    if color != '0':
                        ret.append('N {} {}'.format(color, length))
                        _found_notes += 1

                if _found_notes == 0:
                    # No note, allow bass
                    for note in notes:
                        _, color, length = note.split(' ')
                        ret.append('N {} {}'.format(color, length))
                        break

            return ret

        if diff == 'hard':
            # 2 max chords
            # 0 with one note
            ret = []

            if on_beat:
                # Allow bass and a single note
                for note in notes:
                    _, color, length = note.split(' ')
                    if color == '0':
                        ret.append('N {} {}'.format(color, length))
                        break

                # No bass, allow single note
                for note in notes:
                    _, color, length = note.split(' ')
                    if color == '0':
                        continue
                    ret.append('N {} {}'.format(color, length))
                    break

            elif off_beat:
                for note in notes[:2]:
                    _, color, length = note.split(' ')
                    if len(notes) > 2 and color == '0':
                        continue
                    ret.append('N {} {}'.format(color, length))

            return ret

        return ret

    def parse_expert_part(self, part, part_lines):
        og_part_modified = False
        logger.debug("parsing expert track %s", part)
        difficulty_lines = defaultdict(list)
        notes_by_ms = defaultdict(list)
        for line in part_lines:
            if '=' not in line:
                continue
            ms, value = [_line__part.strip() for _line__part in line.split('=')]
            ms = int(ms)
            notes_by_ms[ms].append(value)
        
        prev_ms_by_diff = {}
        if 'Drums' in part:
            prev_kick = -1000
            for ms, lines in notes_by_ms.items():
                notes = [_line for _line in lines if _line.startswith('N ')]
                for note in notes:
                    _, color, length = note.split(' ')
                    if color == '0':
                        # This is a kick
                        millis_since_last_kick = self.ms_to_real_time_diff(ms, prev_kick)
                        if millis_since_last_kick < 400:
                            logger.info("%s: %s, Converting to 2x kick", ms, millis_since_last_kick)
                            old_note = f"{ms} = N 0 {length}"
                            new_note = f"{ms} = N 32 {length}"
                            for index, line in enumerate(part_lines):
                                if line.strip() == old_note:
                                    part_lines[index] = new_note
                                    og_part_modified = True
                                    break
                        else:
                            prev_kick = ms

        index = 0
        for ms, lines in notes_by_ms.items():
            notes = [_line for _line in lines if _line.startswith('N ')]

            for diff in self.parts_to_generate:
                prev_ms_by_diff[diff] = prev_ms_by_diff.get(diff) or 0
                for non_note_line in lines:
                    if non_note_line in notes:
                        continue
                    difficulty_lines[diff].append('{} = {}'.format(ms, non_note_line))
                if 'Drums' not in part:
                    for easy_note in self.notes_to_diff_single(diff, ms, notes, ms_delta_around=(ms - prev_ms_by_diff[diff])):
                        prev_ms_by_diff[diff] = ms
                        difficulty_lines[diff].append('{} = {}'.format(ms, easy_note))
                else:
                    for easy_note in self.notes_to_diff_drums(diff, ms, notes, ms_delta_around=(ms - prev_ms_by_diff[diff])):
                        prev_ms_by_diff[diff] = ms
                        difficulty_lines[diff].append('{} = {}'.format(ms, easy_note))
            index += 1
        
        for diff in self.parts_to_generate:
            easy_part = part.replace('Expert', diff.capitalize())
            logger.debug("Got new part %s (lines: %s)", easy_part, len(difficulty_lines[diff]))
            self.new_parts[easy_part] = ['{'] + difficulty_lines[diff] + ['}']

        if og_part_modified:
            # possibly modified original part
            self.new_parts[part] = part_lines + ['}']

    def parse_sync_track_part(self, part_lines):
        sync_track = []
        for line in part_lines:
            if '=' not in line:
                continue
            key, value = [_line__part.strip() for _line__part in line.split('=')]
            key = key.strip()
            sync_track.append((key, value))
        self.sync_track = sync_track

    def parse_song_part(self, part_lines):
        logger.debug("parsing song part")
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
            line = line.strip()
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
        part = None
        for line in self.lines:
            line = line.strip()
            if '=' not in line and re.match(r'^.*\[.*\].*$', line):
                part = line.strip()
                parts[part].append(line)
                continue
            elif not part:
                logger.debug("Skipping pre part line %s", line)
                continue

            if line == '}':
                if part:
                    parts[part].append(line)
                    part = None
                    continue

            if part:
                parts[part].append(line)

        added_parts = []
        for partname, lines in parts.items():
            if partname in self.new_parts.keys():
                if self.force_replace_parts:
                    logger.info("Replacing existing part %s", partname)
                    continue
                else:
                    logger.info("Part %s already exists, skipping", partname)
            added_parts.append(partname)
            new_lines.extend(lines)

        for partname, lines in self.new_parts.items():
            if not self.force_replace_parts:
                if partname in parts.keys():
                    continue
            if partname in added_parts:
                continue
            added_parts.append(partname)
            new_lines.append(partname)
            new_lines.extend(lines)

        # Sort newlines, so that lines that start with a number are sorted by number
        lines_by_mode = {
            'start': [],
            'middle': [],
            'end': [],
        }
        mode = "start"
        for line in new_lines:
            starts_with_number = re.match(r'^\d+', line.strip())
            if starts_with_number:
                if mode == "start":
                    mode = "middle"
            else:
                if mode == "middle":
                    mode = "end"
            lines_by_mode[mode].append(line)

        new_lines = lines_by_mode['start'] + sorted(lines_by_mode['middle'], key=lambda l: int(l.split(' ')[0])) + lines_by_mode['end']

        with open(new_filename, 'w') as f:
            f.write('\n'.join(new_lines))


class FileFinder():
    def __init__(self, args):
        self.batch = args.batch
        if args.filename:
            self.path = args.filename
        else:
            self.path = args.directory


    def list_files(self):
        if self.batch:
            # Find all .chart files in path self.path and subfolders
            return [os.path.join(dirpath, f)
                    for dirpath, dirnames, files in os.walk(self.path)
                    for f in files if f.endswith('.chart') and not f.endswith('_easy.chart')]
        else:
            return [self.path]


def ask(question):
    return input(question + ' [y/n] ').lower().startswith('y')


def main(argument_parser_class=argparse.ArgumentParser, ask_func=ask):
    args = parse_args(argument_parser_class=argument_parser_class)
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    filefinder = FileFinder(args)
    file_list = list(filefinder.list_files())
    if len(file_list) == 0:
        logger.error("No files found")
        exit(1)
    if not any(_file.endswith('.chart') for _file in file_list):
        logger.error("No .chart files found (Use --batch if path is a directory)")
        exit(1)
    if len(file_list) > 1:
        # Print files and ask if they are ok
        logger.info("Found {} files:".format(len(file_list)))
        for i, file in enumerate(file_list):
            logger.info("{}".format(file))
        logger.info("")
        if not ask_func("Are these files ok?"):
            logger.error("NO")
            exit(1)

    if args.in_place:
        if not ask_func("Will replace existing files. ARE YOU SURE??"):
            logger.error("NO")
            exit(1)

    for filename in file_list:
        if '.chart' not in filename:
            logger.warning("Skipping file %s (not a .chart)", filename)
            continue
        try:
            with open(filename, 'r') as f:
                lines = [line.strip() for line in f.readlines()]
        except IsADirectoryError:
            logger.error("{} is a directory, use --batch option to parse directories".format(filename))
            exit(1)

        logger.info("Parsing file %s", filename)
        parser = Parser(args)
        parser.parse_file(lines)
        if args.in_place:
            parser.write_file(filename)
            logger.info("Wrote file %s", filename)
        else:
            new_path = filename.replace('.chart', '_easy.chart')
            parser.write_file(new_path)
            logger.info("Wrote file %s", new_path)

        logger.info("")

    logger.info("Done!")


if __name__ == '__main__':
    main()
