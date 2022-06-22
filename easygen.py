import re


filename = sys.argv[1]


def parse_expert_part():
    pass


def parse_file(lines):
    part = None
    part_lines = []
    for line in lines:
        if re.match(r'^[Expert\w*]$', line):
            part = line
            continue
        
        if part:
            part_lines.append(line)


with open(filename, 'r') as f:
    lines = f.readlines()
    parse_file(lines)
