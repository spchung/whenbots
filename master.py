import asyncio
import subprocess
import sys

command = ['python','run_bot.py', '--quoteFundAmount=22','--runSettingId=60db2ea06bc049f8904e560d']

def execute(command):
    # Poll process for new output until finished
    popen = subprocess.Popen(command, stdout=subprocess.PIPE, universal_newlines=True)

    for stdout_line in iter(popen.stdout.readline, ""):
        yield stdout_line 
    
    popen.stdout.close()
    
    return_code = popen.wait()
    
    if return_code:
        raise subprocess.CalledProcessError(return_code, command)

for msg in execute(command):
    print(msg, end="")
