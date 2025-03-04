import argparse
import re
import csv



def processData(input_filename, output_filename):
    with open(input_filename, 'r', encoding='utf-8') as file:
        data = file.read()
        comm_matches = re.findall(r'@COMM\[(\d+)\]: (.+)', data)
        ppid_matches = re.findall(r'@PPID\[(\d+)\]: (\d+)', data)
        cost_matches = re.findall(r'@cost\[(\d+)\]: (\d+)', data)
        comm_dict = {num : string for num, string in comm_matches}
        ppid_dict = {num : value for num, value in ppid_matches}
        cost_dict = {num : value for num, value in cost_matches}
        min_cost = min(int(value) for value in cost_dict.values())
        with open(output_filename, 'w', newline='', encoding='utf-8') as file:
            for num, string in comm_matches:
                ppid = ppid_dict.get(num,'NaN')
                lines = ''
                while ppid != 'NaN':
                    tmp = comm_dict.get(ppid)
                    lines = tmp+';'+lines
                    ppid = ppid_dict.get(ppid,'NaN')
                file.write(f"{lines}")
                file.write(f"{string}")
                cost = cost_dict.get(num,min_cost)
                file.write(f" {cost}\n")

        
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--pkgName', type=str)
    args = parser.parse_args()
    pkgName = args.pkgName

    input_filename = f'./ws/{pkgName}/{pkgName}_data_raw.txt'
    output_filename = f'./ws/{pkgName}/{pkgName}_data_processed.txt'
    processData(input_filename, output_filename)