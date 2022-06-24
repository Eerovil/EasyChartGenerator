
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
    parser = argument_parser_class()
    # Positional arg: filename
    if argument_parser_class is argparse.ArgumentParser:
        parser.add_argument('filename', help='Filename of the file to parse')
    else:
        # Assumed GooeyParser
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

    parser.add_argument('--force', help='If this is given, replace existing parts', action="store_true")

    parser.add_argument('-v', '--verbose', help='Verbose logs', action="store_true")
    return parser.parse_args()


class Parser():
    sync_track = []
    resolution = 192
    new_parts = {}
    lines = []

    def __init__(self, options):
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
        milliseconds -= bpm_ms
        if ms_delta_around is not None:
            if ms_delta_around > (self.resolution * self.custom_note_multiplier * extra_multiplier * beat_multiplier):
                return True
        return milliseconds % int(self.resolution * self.custom_note_multiplier * extra_multiplier * beat_multiplier) == 0

    def notes_to_diff_single(self, diff, ms, notes, ms_delta_around=0):
        ret = []
        if diff == 'easy':
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
                ret.append('N {} {}'.format(color, length))
            return ret

        if diff == 'medium':
            # 4 -> 1
            # Max 2 lenngth chords
            if not self.get_on_beat(ms, ms_delta_around=ms_delta_around):
                return ret
            for note in notes[:2]:
                _, color, length = note.split(' ')
                if color == '4':
                    color = '0'
                ret.append('N {} {}'.format(color, length))
            return ret

        if diff == 'hard':
            if not self.get_on_beat(ms, beat_multiplier=0.5, ms_delta_around=ms_delta_around):
                return []
            return notes

    def notes_to_diff_drums(self, diff, ms, notes, ms_delta_around=0):
        ret = []
        if diff == 'easy':
            # No chords
            if not self.get_on_beat(ms, beat_multiplier=2, ms_delta_around=ms_delta_around):
                return []
            for note in notes:
                _, color, length = note.split(' ')
                return ['N {} {}'.format(color, length)]
            return ret

        if diff == 'medium':
            # 2 max chords
            # 0 only alone
            ret = []
            if not self.get_on_beat(ms, ms_delta_around=ms_delta_around):
                return []
            for note in notes[:2]:
                _, color, length = note.split(' ')
                if len(notes) > 1 and color == '0':
                    continue
                ret.append('N {} {}'.format(color, length))
            return ret

        if diff == 'hard':
            if not self.get_on_beat(ms, ms_delta_around=ms_delta_around):
                return []
            return notes

        return ret

    def parse_expert_part(self, part, part_lines):
        logger.debug("parsing expert track %s", part)
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
            for diff in self.parts_to_generate:
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
        
        for diff in self.parts_to_generate:
            easy_part = part.replace('Expert', diff.capitalize())
            logger.debug("Got new part %s (lines: %s)", easy_part, len(difficulty_lines[diff]))
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
                if self.force_replace_parts:
                    logger.info("Replacing existing part %s", partname)
                    continue
                else:
                    logger.info("Part %s already exists, skipping", partname)
            new_lines.extend(lines)

        for partname, lines in self.new_parts.items():
            if not self.force_replace_parts:
                if partname in parts.keys():
                    continue
            new_lines.append(partname)
            new_lines.extend(lines)
        
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
