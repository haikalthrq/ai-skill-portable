"""Small shared primitives: containment, integrity, portable text and isolation."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import tempfile

TOKEN = '__PORTABLE_HOME__'
SKILL_ROOTS = ['.agents/skills', '.claude/skills', '.config/opencode/skills', '.opencode/skills',
               '.codex/skills', '.gemini/skills', '.gemini/config/skills', '.cline/skills']
TREE_ROOTS = SKILL_ROOTS + ['.config/opencode/commands', '.config/opencode/command',
    '.config/opencode/agents', '.config/opencode/agent', '.config/opencode/plugins',
    '.config/opencode/plugin', '.config/opencode/skill-source-licenses',
    '.opencode/commands', '.opencode/agents', '.opencode/plugins', '.opencode/.opencode/plugins',
    '.local/share/opencode-portable/ecc-runtime']
SAFE_FILES = ['.config/opencode/AGENTS.md', '.config/opencode/opencode.jsonc',
    '.config/opencode/opencode.json', '.config/opencode/package.json', '.config/opencode/package-lock.json',
    '.opencode/opencode.json', '.opencode/package.json', '.opencode/package-lock.json',
    '.opencode/opencode-codex-identity-plugin.ts', '.agents/AGENTS.md', '.agents/.skill-lock.json',
    '.config/opencode/selected-skills-installation.json',
    '.local/state/opencode/model.json', '.config/opencode/tui.json',
    '.claude/CLAUDE.md', '.codex/AGENTS.md', '.gemini/GEMINI.md', '.config/cross-harness-memory/runtime.json']
DENIED_NAMES = {'auth.json', '.npmrc', '.pypirc', '.git-credentials', 'credentials.json',
    'credentials', 'cookies.json', 'session.json', 'tokens.json', 'token.json',
    'storage-state.json', 'storage_state.json', 'storagestate.json', 'auth-state.json',
    'cookies.txt', 'cookiejar.txt', 'cookie-jar.txt'}
SKIP_DIRS = {'node_modules', '.git', '__pycache__', '.cache', '.pytest_cache'}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

def link(path):
    if path.is_symlink():
        return True
    if os.name == 'nt':
        try:
            return bool(getattr(path.lstat(), 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)
        except FileNotFoundError:
            return False
    return False

def allowed(relative):
    return relative in SAFE_FILES or any(relative.startswith(root + '/') for root in TREE_ROOTS)

def logical(relative):
    if not isinstance(relative, str) or not relative:
        raise ValueError('Invalid logical path')
    p = PurePosixPath(relative)
    if p.is_absolute() or '\\' in relative:
        raise ValueError('Invalid logical path')
    if any(x in {'', '.', '..'} or ':' in x for x in relative.split('/')) or not allowed(relative):
        raise ValueError('Path outside the migration allowlist: ' + relative)
    return relative

def contained(home, relative, follow_leaf=False):
    logical(relative)
    destination = home / relative
    current = destination if follow_leaf else destination.parent
    while current != home:
        if link(current):
            raise ValueError('Refusing a redirected parent: ' + relative)
        if current.exists() and not current.is_dir():
            raise ValueError('Destination parent is a file: ' + relative)
        current = current.parent
        if not current.is_relative_to(home):
            raise ValueError('Destination escapes home')
    return destination

def private_path(home, path):
    if not path.is_relative_to(home):
        raise ValueError('Private state escapes home')
    current = path
    while current != home:
        if link(current):
            raise ValueError('Private state is redirected')
        if current.exists() and not current.is_dir():
            raise ValueError('Private state parent is a file')
        current = current.parent
    return path

def blocked(path):
    name = path.name.lower()
    return name in DENIED_NAMES or name.startswith('.env') or path.suffix.lower() in {'.pem', '.key', '.p12', '.pfx', '.db', '.sqlite', '.sqlite3'}

def portable_bytes(data, home):
    try:
        text = data.decode('utf-8')
    except UnicodeDecodeError:
        return data, []
    mappings = [(str(home).replace('\\', '\\\\'), TOKEN), (home.as_posix(), TOKEN), (str(home), TOKEN)]
    changed = []
    project_pattern = r'file:///[a-zA-Z]:/[^)\r\n"<>]*?/RINGKAS(?=/)'
    if re.search(project_pattern, text):
        text = re.sub(project_pattern, 'file:///' + TOKEN + '/Projects/RINGKAS', text)
        changed.append('project-rebase:ringkas')
    for original, replacement in sorted(set(mappings), key=lambda x: -len(x[0])):
        if original and original in text:
            text = text.replace(original, replacement)
            changed.append('home-rebase')
    # Normalise remaining separators inside rebased path segments, including JSON escapes.
    def clean(match):
        return match.group(0).replace('\\\\', '/').replace('\\', '/')
    text = re.sub(TOKEN + r'[^\n\r"\'<>`]*', clean, text)
    return text.encode('utf-8'), sorted(set(changed))

def render(data, home, relative):
    try:
        text = data.decode('utf-8')
    except UnicodeDecodeError:
        return data
    text = text.replace('file:///' + TOKEN, home.as_uri())
    text = text.replace(TOKEN, home.as_posix())
    if os.name != 'nt' and relative == '.opencode/plugins/dcg-guard.js':
        text = text.replace('.split(";")', '.split(process.platform === "win32" ? ";" : ":")')
    return text.encode('utf-8')

def command(args, **kwargs):
    if os.name == 'nt' and args[0] in {'opencode', 'npm', 'npx', 'git', 'gh', 'agent-browser', 'uipro', 'ecc'}:
        executable = args[0] + ('.exe' if args[0] in {'git', 'gh'} else '.cmd')
        args = [executable] + args[1:]
    options = {'check': True, 'text': True, 'encoding': 'utf-8'}
    if 'stdout' in kwargs:
        options['stderr'] = subprocess.PIPE
    else:
        options['capture_output'] = True
    return subprocess.run(args, **options, **kwargs)

def native_catalog(**kwargs):
    # Bun's CLI can exit before a large piped stdout is flushed on Linux.
    # A regular-file sink preserves the complete native JSON output.
    with tempfile.TemporaryFile(mode='w+', encoding='utf-8') as output:
        command(['opencode', 'debug', 'skill'], stdout=output, **kwargs)
        output.seek(0)
        return json.load(output)

def test_temp_root():
    if os.name == 'nt':
        root = Path(tempfile.gettempdir()) / 'opencode'
        root.mkdir(exist_ok=True)
        return root
    return None

def isolated_env(home):
    env = os.environ.copy()
    for key in list(env):
        if key.startswith('OPENCODE_') or key.startswith('ECC_MEMORY_') or re.search(r'(API_KEY|TOKEN|PASSWORD|SECRET)$', key):
            env.pop(key, None)
    env.update({'HOME': str(home), 'USERPROFILE': str(home), 'XDG_CONFIG_HOME': str(home / '.config'),
        'XDG_DATA_HOME': str(home / '.local/share'), 'XDG_CACHE_HOME': str(home / '.cache'),
        'XDG_STATE_HOME': str(home / '.local/state'), 'APPDATA': str(home / 'AppData/Roaming'),
        'LOCALAPPDATA': str(home / 'AppData/Local'), 'OPENCODE_CONFIG_DIR': str(home / '.config/opencode'),
        'OPENCODE_TEST_HOME': str(home), 'PYTHONDONTWRITEBYTECODE': '1', 'IMPECCABLE_NO_UPDATE_CHECK': '1',
        'ECC_MEMORY_HARNESS': 'opencode'})
    bin_directory = home / '.local/share/opencode-portable/tools/node_modules/.bin'
    if bin_directory.is_dir():
        env['PATH'] = str(bin_directory) + os.pathsep + env.get('PATH', '')
    return env

def strip_jsonc(text):
    """Remove comments/trailing commas without changing quoted JSON strings."""
    text = text.lstrip('\ufeff')
    pattern = r'("(?:\\.|[^"\\])*")|//[^\r\n]*|/\*[\s\S]*?\*/'
    text = re.sub(pattern, lambda m: m.group(1) or '', text)
    text = re.sub(r'("(?:\\.|[^"\\])*")|,\s*([}\]])', lambda m: m.group(1) or m.group(2), text)
    return json.loads(text)

def structured_asset(data, suffix):
    declared = suffix.lower() in {'.json', '.jsonc'}
    try:
        text = data.decode('utf-8')
        if declared or text.lstrip('\ufeff \t\r\n').startswith(('{', '[')):
            return strip_jsonc(text)
    except (ValueError, UnicodeDecodeError) as error:
        if declared:
            raise ValueError('Invalid declared JSON/JSONC asset') from error
    return None

SENSITIVE_KEY = re.compile(r'(api.?key|token|password|secret|authorization|credential|^auth$)', re.I)

def session_storage(value):
    if isinstance(value, dict):
        if any(k in value for k in ['access_token', 'refresh_token', 'storageState']):
            return True
        if isinstance(value.get('cookies'), list) and any(isinstance(c, dict) and 'value' in c and 'domain' in c for c in value['cookies']):
            return True
        return any(session_storage(v) for v in value.values())
    if isinstance(value, list):
        return any(session_storage(v) for v in value)
    return False

def structured_credentials(value):
    if isinstance(value, dict):
        for key, item in value.items():
            search_metric = key == 'token_coverage' and isinstance(item, (int, float)) and 0 <= item <= 1
            if not search_metric and SENSITIVE_KEY.search(key) and item and not (isinstance(item, str) and item.startswith('{env:')):
                return True
            if structured_credentials(item):
                return True
    elif isinstance(value, list):
        return any(structured_credentials(v) for v in value)
    return False

def sanitized_config(config, secrets=None):
    required = set()
    def walk(value, path=()):
        if isinstance(value, dict):
            output = {}
            for key, item in value.items():
                header = 'headers' in path and key.lower() not in {'accept', 'content-type', 'user-agent', 'originator'}
                environment = 'environment' in path and key not in {'ECC_MEMORY_HARNESS', 'BROWSER', 'NODE_ENV'}
                secret_key = bool(SENSITIVE_KEY.search(key)) or header or environment
                if secret_key and item and not isinstance(item, str):
                    raise ValueError('Ambiguous credential structure requires explicit mapping: ' + '.'.join(path + (key,)))
                if secret_key and isinstance(item, str) and item and not item.startswith('{env:'):
                    name = 'CONTEXT7_API_KEY' if key == 'CONTEXT7_API_KEY' else 'OPENCODE_PORTABLE_' + re.sub('[^A-Z0-9_]', '_', '_'.join(path + (key,)).upper())
                    output[key] = '{env:' + name + '}'
                    required.add(name)
                    if secrets is not None:
                        secrets.append(item)
                else:
                    output[key] = walk(item, path + (key,))
            return output
        if isinstance(value, list):
            if path and path[-1] == 'command':
                shell = value and isinstance(value[0], str) and Path(value[0]).name.lower().removesuffix('.exe') in {'sh', 'bash', 'zsh', 'cmd', 'powershell', 'pwsh'}
                risky = any(isinstance(v, str) and (re.search(r'^--?[^=]*(?:api[-_]?key|token|password|secret|auth|credential)', v, re.I)
                    or re.search(r'authorization\s*:|\bbearer\s+\S+|(?:api[-_]?key|token|password|secret)\s*[:=]', v, re.I)) for v in value)
                if shell or risky:
                    raise ValueError('Credential-bearing MCP command requires an environment mapping')
            return [walk(item, path) for item in value]
        if isinstance(value, str):
            required.update(re.findall(r'\{env:([^}]+)\}', value))
            if re.search(r'https?://[^\s/:]+:[^\s/@]+@|[?&](?:key|token|password|secret|api_key)=', value, re.I):
                raise ValueError('Credential-bearing URL requires an environment mapping')
        return value
    return walk(config), sorted(required)
