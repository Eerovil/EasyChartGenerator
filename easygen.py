
filename = sys.argv[1]


def parse_expert_part():
    pass


def parse_file(lines):
    for line in lines:
        if re.match(r'^[Expert\w*]$', line):
            continue


with open(filename, 'r') as f:
    lines = f.readlines()
    parse_file(lines)
