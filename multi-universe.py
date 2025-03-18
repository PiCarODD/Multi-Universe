import yaml
import subprocess
import multiprocessing
import sys
import os

def run_tool(tool, target):
    try:
        print(f"\n\033[1;34m[+] Executing {tool['name']} on {target}\033[0m")
        
        # Replace {target} in the flags
        flags = tool['flags'].format(target=target)
        command = [tool['value']] + flags.split()
        
        print(f"\033[1;32mCommand:\033[0m {' '.join(command)}")
        
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"\033[1;31m[-] Error in {tool['name']}:\033[0m {result.stderr}")
        else:
            output_file = f"{target.replace('/', '_')}_{tool['output']}"
            with open(output_file, 'w') as f:
                f.write(result.stdout)
            print(f"\033[1;32m[+] {tool['name']} completed successfully\033[0m")
            print(f"\033[1;36mOutput saved to:\033[0m {output_file}")
    except FileNotFoundError:
        print(f"\033[1;31m[-] {tool['name']} not found. Please install it and try again.\033[0m")
        sys.exit(1)

def process_target(tools, target, include=None, exclude=None):
    print(f"\n\033[1;33m[+] Starting Pentest on {target}\033[0m")
    print("\033[1;33m====================================\033[0m")
    
    # Filter tools based on include/exclude
    filtered_tools = []
    for tool in tools:
        if include and tool['name'] not in include:
            continue
        if exclude and tool['name'] in exclude:
            continue
        filtered_tools.append(tool)
    
    # Group tools by their map value
    tool_groups = {}
    for tool in filtered_tools:
        if tool['map'] not in tool_groups:
            tool_groups[tool['map']] = []
        tool_groups[tool['map']].append(tool)
    
    # Execute tools in order of map value
    for group in sorted(tool_groups.keys()):
        print(f"\n\033[1;35m[+] Running Group {group} Tools on {target}\033[0m")
        processes = []
        for tool in tool_groups[group]:
            p = multiprocessing.Process(target=run_tool, args=(tool, target))
            processes.append(p)
            p.start()
        
        for p in processes:
            p.join()
    
    print(f"\n\033[1;33m[+] Completed Pentest on {target}\033[0m")
    print("\033[1;33m=================================\033[0m")

def validate_config(config):
    """Validate the YAML configuration file"""
    required_sections = ['env', 'tools']
    for section in required_sections:
        if section not in config:
            print(f"\033[1;31m[-] Configuration Error: Missing '{section}' section in YAML file\033[0m")
            return False
    
    # Validate env section
    for env in config['env']:
        if 'name' not in env or 'type' not in env or 'value' not in env:
            print(f"\033[1;31m[-] Configuration Error: Invalid environment configuration\033[0m")
            return False
    
    # Validate tools section
    for tool in config['tools']:
        required_fields = ['name', 'type', 'map', 'value', 'flags', 'output']
        for field in required_fields:
            if field not in tool:
                print(f"\033[1;31m[-] Configuration Error: Tool '{tool.get('name', 'unnamed')}' missing required field: {field}\033[0m")
                return False
        
        if '{target}' not in tool['flags']:
            print(f"\033[1;31m[-] Configuration Error: Tool '{tool['name']}' missing {{target}} placeholder in flags\033[0m")
            return False
    
    return True

def main(config_file):
    if not os.path.exists(config_file):
        print(f"\033[1;31m[-] Configuration Error: Config file {config_file} not found\033[0m")
        sys.exit(1)
    
    with open(config_file, 'r') as f:
        try:
            config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            print(f"\033[1;31m[-] Configuration Error: Invalid YAML format: {str(e)}\033[0m")
            sys.exit(1)
    
    if not validate_config(config):
        print("\n\033[1;33m[!] Configuration Help:")
        print("1. Ensure your YAML file has 'env' and 'tools' sections")
        print("2. Each tool must have: name, type, map, value, flags, output")
        print("3. Use {target} in the flags section to specify target placement")
        print("4. Maintain proper YAML indentation (2 spaces recommended)")
        print("5. Check for missing colons or incorrect data types")
        print("6. Use '#' for comments in the YAML file")
        print("7. Example valid configuration:")
        print("""
env:
  - name: prod networks
    type: io
    value: 127.0.0.1
    include: [nmap, nuclei]  # Optional: only run these tools
    exclude: [httpx]        # Optional: run all except these tools

tools:
  - name: nmap
    type: tool
    map: 1
    value: nmap
    flags: -sV -sC -oN nmap.txt {target}
    output: nmap.txt
\033[0m""")
        sys.exit(1)
    
    if 'tools' in config and 'env' in config:
        # Process each target with its include/exclude settings
        for env in config['env']:
            if env['type'] == 'io':
                include = env.get('include', None)
                exclude = env.get('exclude', None)
                process_target(config['tools'], env['value'], include, exclude)

if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] != '-c':
        print("Usage: multi-universe.py -c config.yml")
        sys.exit(1)
    
    main(sys.argv[2])