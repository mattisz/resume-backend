# Converts Python code into json compatible with cloudformation
# If only an input argument is provided, output file is stored in the same directory, 
# with the same name as the input file .json
# By: Matthew Tiszenkel
# Usage:
# python3 genJSONCode.py input_file.py [output_file.py]

import sys

#gets number of arguments. error if no input file provided
if len(sys.argv) == 1:
    sys.exit("Input file required\nUseage:\ngenJSONCode.py input_file.py [output_file.py]\nOutput file path is optional")
#if only input file is provided, creates output file in same directory as input with the same name as a .json
if len(sys.argv) == 2:
    in_file_split = sys.argv[1].split(".")
    in_file_split.pop()
    out_file = ""
    for word in in_file_split:
        out_file += word + "."
    out_file += "json"
#if user entered an output destination uses that
else:
    out_file = sys.argv[2]

#these lines are required at the start of an inline code block in the cloudformation template
starting_lines = ["\"Code\" : {\n", "    \"ZipFile\" : {\n", "        \"Fn::Join\" : [\n", "            \"\\n\", [\n"]
#these lines are required at the end of an inline code block in the cloudformation template
ending_lines = ["            ]", "        ]", "    }", "}"]

#reads the input file and formats it nicely for json then appends each line to starting_lines
with open(sys.argv[1], 'r') as input:
    for line in input:
        new_line = "                \""
        for char in line:
            if char == "\t":
                new_line += "    "
            elif char == "\"":
                new_line += "\\\""
            elif char == "\r":
                new_line += "\\r"
            elif char == "\n":
                pass
            else:
                new_line += char
        new_line += "\","
        starting_lines.append(new_line)
        starting_lines.append("\n")

#removes last newline from starting_lines
starting_lines.pop()

#removes the traling comma from last line of starting_lines
starting_lines[-1] = starting_lines[-1].rstrip(starting_lines[-1][-1])

#writes the new json file
with open(out_file, 'w') as output:
    for line in starting_lines:
        output.write(line)
    for line in ending_lines:
        output.write("\n")
        output.write(line)