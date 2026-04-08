import os
import yaml
import json
import glob

# Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
K8S_DIR = os.path.join(BASE_DIR, "k8s")
MONITORING_DIR = os.path.join(BASE_DIR, "monitoring")
TESTS_DIR = os.path.join(BASE_DIR, "tests")
OUTPUT_COMPOSE_FILE = "docker-compose.health.yml"
INVENTORY_FILE = "health_check_inventory.json"
ENV_FILE = os.path.join(BASE_DIR, ".env")

def load_env_file(env_path):
    env_vars = {}
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        k, v = line.split('=', 1)
                        env_vars[k.strip()] = v.strip()
    return env_vars

GLOBAL_ENV = load_env_file(ENV_FILE)

def parse_k8s_manifests(k8s_dir):
    services = {}
    
    # Find all yaml files
    yaml_files = glob.glob(os.path.join(k8s_dir, "*.yaml")) + glob.glob(os.path.join(k8s_dir, "*.yml"))
    
    for file_path in yaml_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                docs = yaml.safe_load_all(f)
                for doc in docs:
                    if not doc:
                        continue
                    
                    kind = doc.get('kind')
                    metadata = doc.get('metadata', {})
                    metadata.get('name')
                    
                    if kind in ['Deployment', 'StatefulSet', 'DaemonSet']:
                        spec = doc.get('spec', {}).get('template', {}).get('spec', {})
                        containers = spec.get('containers', [])
                        
                        for container in containers:
                            container_name = container.get('name')
                            image = container.get('image')
                            ports = [p.get('containerPort') for p in container.get('ports', [])]
                            env = container.get('env', [])
                            env_from = container.get('envFrom', [])
                            resources = container.get('resources', {})
                            liveness = container.get('livenessProbe')
                            readiness = container.get('readinessProbe')
                            startup = container.get('startupProbe')
                            
                            # Construct service definition
                            service_def = {
                                'name': container_name,
                                'image': image,
                                'ports': ports,
                                'env': env,
                                'env_from': env_from,
                                'resources': resources,
                                'probes': {
                                    'liveness': liveness,
                                    'readiness': readiness,
                                    'startup': startup
                                },
                                'source_file': file_path,
                                'k8s_kind': kind
                            }
                            services[container_name] = service_def
                            
            except Exception as e:
                print(f"Error parsing {file_path}: {e}")
                
    return services

def parse_monitoring_configs(monitoring_dir):
    rules = []
    # Find prometheus rules
    rule_files = glob.glob(os.path.join(monitoring_dir, "**/*.yml"), recursive=True) + \
                 glob.glob(os.path.join(monitoring_dir, "**/*.yaml"), recursive=True)
                 
    for file_path in rule_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                doc = yaml.safe_load(f)
                if not doc:
                    continue
                    
                # Check for Prometheus rule format
                if 'groups' in doc:
                    for group in doc['groups']:
                        for rule in group.get('rules', []):
                            if 'alert' in rule:
                                rules.append({
                                    'alert': rule['alert'],
                                    'expr': rule['expr'],
                                    'for': rule.get('for'),
                                    'labels': rule.get('labels', {}),
                                    'annotations': rule.get('annotations', {}),
                                    'source_file': file_path
                                })
            except Exception:
                pass # Ignore non-yaml or irrelevant files
    return rules

def find_tests(tests_dir):
    test_files = []
    # Simple walk to find test files
    for root, _, files in os.walk(tests_dir):
        for file in files:
            if file.startswith("test_") and file.endswith(".py"):
                test_files.append({
                    'path': os.path.join(root, file),
                    'type': 'python'
                })
            elif file.endswith("_test.go"):
                test_files.append({
                    'path': os.path.join(root, file),
                    'type': 'go'
                })
            elif file.endswith("smoke_test.json"):
                test_files.append({
                    'path': os.path.join(root, file),
                    'type': 'json_scenario'
                })
    return test_files

def map_monitoring_to_services(services, rules):
    # Heuristic mapping
    for service_name, service in services.items():
        service['monitoring_rules'] = []
        for rule in rules:
            # Check if service name is in the alert name or expression or annotations
            rule_str = json.dumps(rule).lower()
            if service_name.lower() in rule_str:
                service['monitoring_rules'].append(rule)
            # Add generic rules if they seem applicable (e.g., "ServiceDown" or "HighCpu")
            elif "instance" in rule.get('annotations', {}).get('summary', ""):
                # Generic rule, likely applies to all
                service['monitoring_rules'].append(rule)

def generate_docker_compose(services):
    compose = {
        'services': {},
        'networks': {
            'hypercode-net': {
                'driver': 'bridge'
            }
        },
        'volumes': {
            'postgres_data': {},
            'redis_data': {}
        }
    }
    
    for name, service in services.items():
        # Clean up image name if it's a local reference that needs building or specific tagging
        image = service['image']
        
        # Compose Service Definition
        comp_svc = {
            'image': image,
            'container_name': name,
            'networks': ['hypercode-net'],
            'restart': 'always'
        }
        
        # Ports
        if service['ports']:
            # Map container port to ephemeral host port to avoid conflicts
            comp_svc['ports'] = [f"{p}" for p in service['ports']]
            
        # Environment
        env_vars = {}
        # Apply global env vars first if they match common keys
        for k, v in GLOBAL_ENV.items():
            if k in ['POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_DB', 'API_KEY', 'JWT_SECRET', 'OPENAI_API_KEY', 'PERPLEXITY_API_KEY', 'DISCORD_TOKEN', 'DISCORD_BOT_TOKEN', 'DISCORD_CLIENT_ID', 'DISCORD_CLIENT_SECRET']:
                env_vars[k] = v
            # Ensure DB URL is injected even if not in manifest
            if k == 'HYPERCODE_DB_URL' and 'DATABASE_URL' not in [e.get('name') for e in service['env'] if isinstance(e, dict)]:
                 env_vars['DATABASE_URL'] = v.replace('localhost', 'postgres')

        # Handle envFrom (secrets/configmaps) - simplistic mapping
        if service['env_from']:
            # In a real generator, we'd look up the ConfigMap/Secret. 
            pass
            
        # Handle explicit env
        for e in service['env']:
            if isinstance(e, dict):
                k = e.get('name')
                v = e.get('value')
                if v is not None:
                    env_vars[k] = v
                else:
                    # valueFrom - simplified handling
                    if k in GLOBAL_ENV:
                        env_vars[k] = GLOBAL_ENV[k]
                    elif "POSTGRES_USER" in k:
                        env_vars[k] = GLOBAL_ENV.get('POSTGRES_USER', 'postgres')
                    elif "POSTGRES_PASSWORD" in k:
                        env_vars[k] = GLOBAL_ENV.get('POSTGRES_PASSWORD', 'postgres')
                    elif "POSTGRES_DB" in k:
                        env_vars[k] = GLOBAL_ENV.get('POSTGRES_DB', 'hypercode')
                    elif "DB_URL" in k or "DATABASE_URL" in k:
                        # Use internal docker network hostname 'postgres'
                        env_vars[k] = GLOBAL_ENV.get('HYPERCODE_DB_URL', "postgresql://postgres:postgres@postgres:5432/hypercode")
                        # Force internal hostname if using localhost from .env
                        if "localhost" in env_vars[k]:
                            env_vars[k] = env_vars[k].replace("localhost", "postgres")
                    elif "REDIS_URL" in k or "CELERY_BROKER_URL" in k:
                        env_vars[k] = GLOBAL_ENV.get('HYPERCODE_REDIS_URL', "redis://redis:6379/0")
                    elif "API_KEY" in k:
                         env_vars[k] = GLOBAL_ENV.get('API_KEY', 'dev-key')
                    else:
                         # Fallback to dummy if not in .env
                         env_vars[k] = "dummy_value_for_health_check" 

        comp_svc['environment'] = env_vars
        
        # Add depends_on for core services
        if name == 'hypercode-core':
            comp_svc['depends_on'] = {
                'postgres': {'condition': 'service_healthy'},
                'redis': {'condition': 'service_healthy'}
            }
        elif name == 'crew-orchestrator':
             comp_svc['depends_on'] = {
                'hypercode-core': {'condition': 'service_healthy'},
                'redis': {'condition': 'service_healthy'}
            }
        elif name in ['celery-worker', 'frontend-specialist', 'backend-specialist', 'database-architect', 'qa-engineer', 'devops-engineer', 'security-engineer', 'system-architect', 'project-strategist']:
             comp_svc['depends_on'] = {
                'crew-orchestrator': {'condition': 'service_started'}, # Orchestrator might take time to be healthy
                'redis': {'condition': 'service_healthy'}
            }
            
        # Resources (simplified translation)
        if service['resources']:
            # Docker Compose v3 resources are under deploy
            limits = service['resources'].get('limits', {})
            service['resources'].get('requests', {})
            
            comp_svc['deploy'] = {
                'resources': {
                    'limits': {},
                    'reservations': {}
                }
            }
            if 'memory' in limits:
                mem = limits['memory']
                # Normalize K8s units (Mi/Gi) to Docker (m/g)
                if isinstance(mem, str):
                    mem = mem.replace('Mi', 'm').replace('Gi', 'g').replace('Ti', 't')
                    mem = mem.replace('mi', 'm').replace('gi', 'g') # Handle lowercase
                comp_svc['deploy']['resources']['limits']['memory'] = mem
            if 'cpu' in limits:
                 cpu_val = limits['cpu']
                 # Normalize K8s cpu units (m) to Docker (cores)
                 # 1000m = 1 core
                 if isinstance(cpu_val, str) and cpu_val.endswith('m'):
                     try:
                         cpu_float = float(cpu_val.rstrip('m')) / 1000.0
                         comp_svc['deploy']['resources']['limits']['cpus'] = f"{cpu_float}"
                     except:
                         comp_svc['deploy']['resources']['limits']['cpus'] = "0.5" # Fallback
                 else:
                     comp_svc['deploy']['resources']['limits']['cpus'] = str(cpu_val)
        
        # Override CPU/Memory limits for heavy services in health check mode to prevent OOM/CPU throttling on local machine
        if name in ['ollama', 'postgres', 'hypercode-core', 'crew-orchestrator']:
             if 'deploy' not in comp_svc: comp_svc['deploy'] = {'resources': {'limits': {}}}
             comp_svc['deploy']['resources']['limits']['cpus'] = "2.0" # Increased from 1.0
             comp_svc['deploy']['resources']['limits']['memory'] = "4g" # Increased from 2g
                
        # Probes -> Healthcheck
        # We prioritize Readiness, then Liveness
        probe = service['probes']['readiness'] or service['probes']['liveness']
        if probe:
            health = {}
            if 'httpGet' in probe:
                path = probe['httpGet'].get('path', '/')
                port = probe['httpGet'].get('port', 80)
                # Docker healthcheck command
                health['test'] = ["CMD", "curl", "-f", f"http://localhost:{port}{path}"]
                
                # SPECIAL OVERRIDE FOR HYPERCODE CORE
                # The k8s manifest says port 8000, but app might be binding differently or probe path is wrong.
                # Force simple curl check if it's hypercode-core
                if name == 'hypercode-core':
                     health['test'] = ["CMD", "curl", "-f", "http://localhost:8000/health"]
            elif 'exec' in probe:
                health['test'] = ["CMD"] + probe['exec']['command']
            elif 'tcpSocket' in probe:
                port = probe['tcpSocket'].get('port')
                health['test'] = ["CMD-SHELL", f"nc -z localhost {port} || exit 1"]
            
            # Relax health checks for stability in dev/test env
            if 'initialDelaySeconds' in probe:
                health['start_period'] = f"{max(int(probe['initialDelaySeconds']), 30)}s" # Minimum 30s start period
            if 'periodSeconds' in probe:
                health['interval'] = f"{probe['periodSeconds']}s"
            if 'timeoutSeconds' in probe:
                health['timeout'] = f"{probe['timeoutSeconds']}s"
            if 'failureThreshold' in probe:
                health['retries'] = max(int(probe['failureThreshold']), 5) # Ensure at least 5 retries
            
            # Special overrides for HyperCode Core
            if name == 'hypercode-core':
                health['start_period'] = "120s" # Give it MORE time to start up and connect to DB
                health['retries'] = 20
                health['interval'] = "10s"
                
            if health:
                comp_svc['healthcheck'] = health

        # Special overrides for known troublesome services
        if name == 'postgres':
             comp_svc['healthcheck'] = {
                'test': ["CMD-SHELL", "pg_isready -U postgres"],
                'interval': "5s",
                'timeout': "5s",
                'retries': 10,
                'start_period': "10s"
            }
        
        if name == 'ollama':
             # Ollama needs to pull the model on first run, which takes time
             # We override the command to pull the model if not present
             model = "qwen2.5-coder:7b"
             # Custom entrypoint to pull model in background
             comp_svc['entrypoint'] = ["/bin/sh", "-c", f"ollama serve & sleep 5 && ollama pull {model} && wait"]
             comp_svc['healthcheck'] = {
                'test': ["CMD", "curl", "-f", "http://localhost:11434"],
                'interval': "30s",
                'timeout': "10s",
                'retries': 10,
                'start_period': "60s"
            }

        compose['services'][name] = comp_svc

    # Add Postgres and Redis if not present but referenced
    if 'postgres' not in compose['services']:
        compose['services']['postgres'] = {
            'image': 'postgres:15-alpine',
            'container_name': 'postgres',
            'environment': {
                'POSTGRES_USER': 'postgres',
                'POSTGRES_PASSWORD': 'postgres',
                'POSTGRES_DB': 'hypercode'
            },
            'networks': ['hypercode-net'],
            'ports': ['5432:5432'],
            'healthcheck': {
                'test': ["CMD-SHELL", "pg_isready -U postgres"],
                'interval': "10s",
                'timeout': "5s",
                'retries': 5
            }
        }
        
    if 'redis' not in compose['services']:
        compose['services']['redis'] = {
            'image': 'redis:7-alpine',
            'container_name': 'redis',
            'networks': ['hypercode-net'],
            'ports': ['6379:6379'],
            'healthcheck': {
                'test': ["CMD", "redis-cli", "ping"],
                'interval': "10s",
                'timeout': "5s",
                'retries': 5
            }
        }
        
    return compose

def main():
    print(f"Scanning K8s manifests in {K8S_DIR}...")
    services = parse_k8s_manifests(K8S_DIR)
    
    print(f"Scanning Monitoring configs in {MONITORING_DIR}...")
    rules = parse_monitoring_configs(MONITORING_DIR)
    
    print(f"Scanning Tests in {TESTS_DIR}...")
    tests = find_tests(TESTS_DIR)
    
    print("Mapping Monitoring Rules...")
    map_monitoring_to_services(services, rules)
    
    print("Generating Docker Compose...")
    compose_config = generate_docker_compose(services)
    
    with open(OUTPUT_COMPOSE_FILE, 'w', encoding='utf-8') as f:
        yaml.dump(compose_config, f, sort_keys=False)
        
    print(f"Generated {OUTPUT_COMPOSE_FILE}")
    
    # Generate Inventory JSON for Controller
    inventory = {
        'services': services,
        'tests': tests,
        'compose_file': OUTPUT_COMPOSE_FILE
    }
    
    with open(INVENTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(inventory, f, indent=2, default=str)
        
    print(f"Generated {INVENTORY_FILE}")

if __name__ == "__main__":
    main()
