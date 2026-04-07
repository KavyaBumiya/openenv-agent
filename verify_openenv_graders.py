import yaml

with open('openenv.yaml', 'r') as f:
    config = yaml.safe_load(f)

print('✅ openenv.yaml parsed successfully')
print(f'Tasks defined: {len(config["tasks"])}')
print()
print('Task Grader Configuration:')
for task in config['tasks']:
    grader = task.get('grader', 'MISSING')
    status = '✅' if grader != 'MISSING' else '❌'
    print(f'  {status} {task["name"]}: grader={grader}')
